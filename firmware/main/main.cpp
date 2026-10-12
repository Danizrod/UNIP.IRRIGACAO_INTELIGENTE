#include "controller.hpp"
#include "cJSON.h"
#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_netif_sntp.h"
#include "esp_task_wdt.h"
#include "esp_timer.h"
#include "esp_random.h"
#include "esp_wifi.h"
#include "mqtt_client.h"
#include "nvs_flash.h"
#include <cstring>
#include <ctime>
#include <cstdlib>
#include <cctype>
#include <atomic>
#if CONFIG_IRRIGATION_PHYSICAL_ENABLED
#error "Physical actuation unavailable: validate hardware and implement reviewed drivers first"
#endif

using namespace irrigation;
static constexpr const char* TAG="irrigation";
// No GPIO driver exists until actual components and calibration are reviewed.
struct DisabledPump:Actuator{
 bool enabled=false;
 void off()override{enabled=false;}
 bool on()override{
#if CONFIG_IRRIGATION_SIMULATION
  enabled=true;return true;
#else
  return false;
#endif
 }
} pump;
struct NvsJournal:Journal {
 nvs_handle_t handle=0; bool ready=false;
 NvsJournal(){ready=nvs_open("commands",NVS_READWRITE,&handle)==ESP_OK;}
 bool contains(const std::string&id)override{
  if(!ready)return true;
  for(unsigned i=0;i<128;++i){char key[12],value[96];size_t size=sizeof(value);snprintf(key,sizeof(key),"id%u",i);
   if(nvs_get_str(handle,key,value,&size)==ESP_OK&&id==value)return true;}
  return false;
 }
 bool reserve(const std::string&id)override{
  if(!ready||id.size()>95)return false;
  for(unsigned i=0;i<128;++i){char key[12];size_t size=0;snprintf(key,sizeof(key),"id%u",i);
   if(nvs_get_str(handle,key,nullptr,&size)==ESP_ERR_NVS_NOT_FOUND)
    return nvs_set_str(handle,key,id.c_str())==ESP_OK&&nvs_commit(handle)==ESP_OK;}
  return false;
 }
 int64_t last_cycle_at()override{int64_t value=0;if(!ready)return INT64_MAX;auto result=nvs_get_i64(handle,"cycle_at",&value);return result==ESP_OK||result==ESP_ERR_NVS_NOT_FOUND?value:INT64_MAX;}
 bool record_cycle_at(int64_t value)override{return ready&&nvs_set_i64(handle,"cycle_at",value)==ESP_OK&&nvs_commit(handle)==ESP_OK;}
};
static Controller* controller=nullptr;
static esp_mqtt_client_handle_t mqtt=nullptr;
static std::string device,broker,username,password,ca,ssid,wifi_password,ntp,experiment,unit;
struct Message {std::string topic,payload;};
static Buffer<Message> outbox(32);
static Sensors sensors; // Invalid by default; no fabricated physical measurements.
static bool connected=false;
static bool subscribed=false;
static std::atomic<bool> utc_synced{false};
static void clock_synced(timeval*){utc_synced.store(true);}
static int in_flight=-1;
static SemaphoreHandle_t mutex;
static std::string uuid(){
 uint8_t b[16];esp_fill_random(b,sizeof(b));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;char s[37];
 snprintf(s,sizeof(s),"%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",b[0],b[1],b[2],b[3],b[4],b[5],b[6],b[7],b[8],b[9],b[10],b[11],b[12],b[13],b[14],b[15]);return s;
}
static std::string get(nvs_handle_t h,const char*key){size_t n=0;if(nvs_get_str(h,key,nullptr,&n)!=ESP_OK||!n)return {};std::string s(n,'\0');if(nvs_get_str(h,key,s.data(),&n)!=ESP_OK)return {};s.resize(n-1);return s;}
static int64_t epoch(){return static_cast<int64_t>(time(nullptr));}
static std::string event_stamp(){
 timeval tv;gettimeofday(&tv,nullptr);tm utc;gmtime_r(&tv.tv_sec,&utc);char base[24],stamp[40];
 strftime(base,sizeof(base),"%Y-%m-%dT%H:%M:%S",&utc);
 snprintf(stamp,sizeof(stamp),"%s.%06ldZ",base,static_cast<long>(tv.tv_usec));return stamp;
}
static const char* source(){
#if CONFIG_IRRIGATION_SIMULATION
 return "simulation";
#else
 return "physical";
#endif
}
static const char* str(cJSON*j,const char*k){auto v=cJSON_GetObjectItemCaseSensitive(j,k);return cJSON_IsString(v)?v->valuestring:nullptr;}
static double num(cJSON*j,const char*k){auto v=cJSON_GetObjectItemCaseSensitive(j,k);return cJSON_IsNumber(v)?v->valuedouble:NAN;}
static bool valid_uuid(const char*s){
 if(!s||strlen(s)!=36)return false;
 for(size_t i=0;i<36;++i){bool separator=i==8||i==13||i==18||i==23;if(separator?s[i]!='-':!std::isxdigit(static_cast<unsigned char>(s[i])))return false;}
 return true;
}
static int64_t iso(const char*s){
 if(!s||strlen(s)<20||strlen(s)>32)return 0;
 int y,m,d,h,min;double sec;char zone[8]={};
 if(sscanf(s,"%4d-%2d-%2dT%2d:%2d:%lf%7s",&y,&m,&d,&h,&min,&sec,zone)!=7||(strcmp(zone,"Z")&&strcmp(zone,"+00:00")))return 0;
 if(y<2020||y>2100||m<1||m>12||d<1||d>31||h<0||h>23||min<0||min>59||!std::isfinite(sec)||sec<0||sec>=60)return 0;
 tm t={};t.tm_year=y-1900;t.tm_mon=m-1;t.tm_mday=d;t.tm_hour=h;t.tm_min=min;t.tm_sec=static_cast<int>(sec);
 auto result=mktime(&t);return t.tm_year==y-1900&&t.tm_mon==m-1&&t.tm_mday==d?result:0;
}
static void mqtt_event(void*,esp_event_base_t,int32_t id,void*data){
 xSemaphoreTake(mutex,portMAX_DELAY);
 auto e=static_cast<esp_mqtt_event_handle_t>(data);
 if(id==MQTT_EVENT_CONNECTED){connected=true;controller->connectivity(true);esp_mqtt_client_subscribe(mqtt,("irrigation/v1/"+device+"/commands").c_str(),1);
  // Main loop opens the remote barrier only after subscription/clock/backlog checks.
 }else if(id==MQTT_EVENT_DISCONNECTED){connected=false;subscribed=false;controller->connectivity(false);}
 else if(id==MQTT_EVENT_SUBSCRIBED){subscribed=true;}
 else if(id==MQTT_EVENT_PUBLISHED&&e->msg_id==in_flight){outbox.acknowledged();in_flight=-1;}
 else if(id==MQTT_EVENT_DELETED&&e->msg_id==in_flight){in_flight=-1;}
 else if(id==MQTT_EVENT_DATA){
  if(e->total_data_len!=e->data_len||e->current_data_offset||e->data_len>2048){xSemaphoreGive(mutex);return;}
  if(std::string(e->topic,e->topic_len)!="irrigation/v1/"+device+"/commands"){xSemaphoreGive(mutex);return;}
  auto j=cJSON_ParseWithLength(e->data,e->data_len);if(!j){xSemaphoreGive(mutex);return;}
  auto cid=str(j,"command_id"),dev=str(j,"device_id"),source=str(j,"source");
  auto experiment=str(j,"experiment_id"),unit=str(j,"unit_id"),treatment=str(j,"treatment"),reason=str(j,"reason");
  if(valid_uuid(cid)&&dev&&source&&experiment&&unit&&treatment&&reason&&device==dev&&::experiment==experiment&&::unit==unit&&num(j,"schema_version")==1&&!strcmp(source,::source())&&(!strcmp(treatment,"T1")||!strcmp(treatment,"T2")||!strcmp(treatment,"T3"))){
   Command c{cid,iso(str(j,"issued_at")),iso(str(j,"expires_at")),num(j,"target_volume_ml"),num(j,"max_duration_s")};
   if(c.expires_at-c.issued_at<=300&&c.duration_s<=300)controller->submit(c,sensors,epoch());
  }
  cJSON_Delete(j);
 }
 xSemaphoreGive(mutex);
}
static void wifi_event(void*,esp_event_base_t base,int32_t id,void*){
 if(base==WIFI_EVENT&&id==WIFI_EVENT_STA_START)esp_wifi_connect();
 if(base==WIFI_EVENT&&id==WIFI_EVENT_STA_DISCONNECTED)esp_wifi_connect();
 if(base==IP_EVENT&&id==IP_EVENT_STA_GOT_IP&&!ntp.empty())esp_netif_sntp_start();
}
static void queue_events(){
 for(auto&e:controller->events){
  auto j=cJSON_CreateObject();cJSON_AddNumberToObject(j,"schema_version",1);
  auto eid=uuid();cJSON_AddStringToObject(j,"event_id",eid.c_str());
  cJSON_AddStringToObject(j,"command_id",e.command_id.c_str());cJSON_AddStringToObject(j,"device_id",device.c_str());
  cJSON_AddStringToObject(j,"source",source());auto stamp=event_stamp();
  cJSON_AddStringToObject(j,"origin",e.local?"local":"remote");
  cJSON_AddStringToObject(j,"experiment_id",experiment.c_str());cJSON_AddStringToObject(j,"unit_id",unit.c_str());
  cJSON_AddBoolToObject(j,"measurements_valid",false);
  cJSON_AddStringToObject(j,"occurred_at",stamp.c_str());cJSON_AddStringToObject(j,"status",e.status.c_str());cJSON_AddStringToObject(j,"reason",e.reason.c_str());
  char*s=cJSON_PrintUnformatted(j);if(s){outbox.push({"irrigation/v1/"+device+"/events",s});free(s);}cJSON_Delete(j);
 }controller->events.clear();
}
static void queue_synthetic_telemetry(){
#if CONFIG_IRRIGATION_SIMULATION
 auto j=cJSON_CreateObject();cJSON_AddNumberToObject(j,"schema_version",1);
 auto id=uuid();cJSON_AddStringToObject(j,"message_id",id.c_str());
 cJSON_AddStringToObject(j,"device_id",device.c_str());cJSON_AddStringToObject(j,"experiment_id",experiment.c_str());cJSON_AddStringToObject(j,"unit_id",unit.c_str());
 cJSON_AddStringToObject(j,"treatment","T2");cJSON_AddStringToObject(j,"source","simulation");
 char stamp[32];time_t now=time(nullptr);tm utc;gmtime_r(&now,&utc);strftime(stamp,sizeof(stamp),"%Y-%m-%dT%H:%M:%SZ",&utc);cJSON_AddStringToObject(j,"collected_at",stamp);
 cJSON_AddStringToObject(j,"calibration_id","simulation-fixture-only");cJSON_AddNumberToObject(j,"soil_raw",2000);cJSON_AddNumberToObject(j,"soil_index",sensors.soil);cJSON_AddBoolToObject(j,"sensor_valid",true);
 cJSON_AddNumberToObject(j,"temperature_c",23);cJSON_AddNumberToObject(j,"humidity_pct",50);cJSON_AddNumberToObject(j,"reservoir_mass_g",sensors.available_ml);
 char*s=cJSON_PrintUnformatted(j);if(s){outbox.push({"irrigation/v1/"+device+"/telemetry",s});free(s);}cJSON_Delete(j);
#endif
}
extern "C" void app_main(){
 pump.off(); // First application action; physical driver intentionally absent.
 setenv("TZ","UTC0",1);tzset();
 if(nvs_flash_init()!=ESP_OK){ESP_LOGE(TAG,"NVS unavailable; locked off");return;}
 static NvsJournal journal;
 mutex=xSemaphoreCreateMutex();
 nvs_handle_t settings;
 if(nvs_open("settings",NVS_READONLY,&settings)==ESP_OK){
  device=get(settings,"device");broker=get(settings,"broker");username=get(settings,"username");password=get(settings,"password");ca=get(settings,"ca");ssid=get(settings,"ssid");wifi_password=get(settings,"wifi_password");ntp=get(settings,"ntp");experiment=get(settings,"experiment");unit=get(settings,"unit");nvs_close(settings);
 }
 Limits limits{};
#if CONFIG_IRRIGATION_SIMULATION
 // Explicit synthetic fixture limits, never physical calibration.
 if(device.rfind("sim-",0)!=0||experiment.rfind("sim-",0)!=0){ESP_LOGE(TAG,"Simulation requires sim- identities");return;}
 limits=Limits{true,50,10,30,60,20,5};
#endif
 static Controller core(limits,journal,pump,uuid);controller=&core;
 if(!device.empty()&&broker.rfind("mqtts://",0)==0&&!username.empty()&&!password.empty()&&!ca.empty()&&!ssid.empty()&&!ntp.empty()){
  ESP_ERROR_CHECK(esp_netif_init());ESP_ERROR_CHECK(esp_event_loop_create_default());esp_netif_create_default_wifi_sta();wifi_init_config_t init=WIFI_INIT_CONFIG_DEFAULT();ESP_ERROR_CHECK(esp_wifi_init(&init));
  esp_sntp_config_t clock=ESP_NETIF_SNTP_DEFAULT_CONFIG(ntp.c_str());clock.start=false;clock.sync_cb=clock_synced;ESP_ERROR_CHECK(esp_netif_sntp_init(&clock));
  esp_mqtt_client_config_t cfg={};cfg.broker.address.uri=broker.c_str();cfg.broker.verification.certificate=ca.c_str();cfg.credentials.username=username.c_str();cfg.credentials.authentication.password=password.c_str();cfg.credentials.client_id=device.c_str();
  mqtt=esp_mqtt_client_init(&cfg);esp_mqtt_client_register_event(mqtt,static_cast<esp_mqtt_event_id_t>(ESP_EVENT_ANY_ID),mqtt_event,nullptr);
  ESP_ERROR_CHECK(esp_event_handler_register(WIFI_EVENT,ESP_EVENT_ANY_ID,wifi_event,nullptr));ESP_ERROR_CHECK(esp_event_handler_register(IP_EVENT,IP_EVENT_STA_GOT_IP,wifi_event,nullptr));
  wifi_config_t w={};strncpy(reinterpret_cast<char*>(w.sta.ssid),ssid.c_str(),sizeof(w.sta.ssid)-1);strncpy(reinterpret_cast<char*>(w.sta.password),wifi_password.c_str(),sizeof(w.sta.password)-1);w.sta.threshold.authmode=WIFI_AUTH_WPA2_PSK;
  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA,&w));ESP_ERROR_CHECK(esp_wifi_start());
 }else ESP_LOGW(TAG,"No complete TLS/Wi-Fi credentials; offline locked-off firmware");
 esp_task_wdt_add(nullptr);
 bool mqtt_started=false;
 int64_t last_telemetry=0;
 size_t reported_dropped=0;
 for(;;){if(mqtt&&!mqtt_started&&utc_synced.load()&&epoch()>1700000000){mqtt_started=esp_mqtt_client_start(mqtt)==ESP_OK;}
  xSemaphoreTake(mutex,portMAX_DELAY);
#if CONFIG_IRRIGATION_SIMULATION
  sensors.valid=utc_synced.load();sensors.soil=40;sensors.available_ml=sensors.removed_ml<1000?1000-sensors.removed_ml:0;sensors.sampled_at=epoch();
  if(pump.enabled)sensors.removed_ml+=0.1; // Synthetic withdrawal only, not a calibrated flow.
#endif
  controller->tick(sensors,epoch());queue_events();
  if(utc_synced.load()&&epoch()>1700000000&&epoch()-last_telemetry>=5){queue_synthetic_telemetry();last_telemetry=epoch();}
  if(connected&&subscribed&&utc_synced.load()&&epoch()>1700000000&&outbox.size()==0&&in_flight<0&&!controller->running())controller->synchronize(epoch());
  // PUBACK only releases the delivery buffer; it never proves physical actuation.
  if(connected&&outbox.front()&&in_flight<0){in_flight=esp_mqtt_client_publish(mqtt,outbox.front()->topic.c_str(),outbox.front()->payload.c_str(),0,1,0);}
  if(outbox.dropped!=reported_dropped){ESP_LOGW(TAG,"Outbound overflow: %u messages lost",static_cast<unsigned>(outbox.dropped));reported_dropped=outbox.dropped;}
  xSemaphoreGive(mutex);esp_task_wdt_reset();vTaskDelay(pdMS_TO_TICKS(100));}
}
