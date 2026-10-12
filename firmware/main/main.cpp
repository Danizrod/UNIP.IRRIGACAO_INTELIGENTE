#include "controller.hpp"
#include "retention.hpp"
#include "durable_buffer.hpp"
#include "shared_rig.hpp"
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
#include <cstddef>
#if CONFIG_IRRIGATION_PHYSICAL_ENABLED
#error "Physical actuation unavailable: validate hardware and implement reviewed drivers first"
#endif

using namespace irrigation;
static constexpr const char* TAG="irrigation";
// No GPIO driver exists until actual components and calibration are reviewed.
struct DisabledPump:ChannelDriver{
 int channel=-1;
 void off_all()override{channel=-1;}
 bool on(size_t index)override{
#if CONFIG_IRRIGATION_SIMULATION
  if(channel>=0)return false;
  channel=static_cast<int>(index);return true;
#else
  (void)index;
  return false;
#endif
 }
} pump;
static nvs_handle_t journal_handle=0,event_handle=0;
static const JournalState& load_journal(){
 static JournalState state;
 if(nvs_flash_init_partition("journal")!=ESP_OK||nvs_open_from_partition("journal","commands",NVS_READWRITE,&journal_handle)!=ESP_OK){state.version=0;return state;}
 size_t length=sizeof(state);auto result=nvs_get_blob(journal_handle,"state",&state,&length);
 if(result==ESP_OK){if(length<offsetof(JournalState,slots)||length>sizeof(state)||(length-offsetof(JournalState,slots))%sizeof(JournalSlot))state.version=0;return state;}
 if(result!=ESP_ERR_NVS_NOT_FOUND){state.version=0;return state;}
 // Read-only migration: preserve the original default-NVS namespace completely.
 nvs_handle_t legacy;
 result=nvs_open("commands",NVS_READONLY,&legacy);
 if(result==ESP_ERR_NVS_NOT_FOUND)return state;
 if(result!=ESP_OK){state.version=0;return state;}
 for(unsigned i=0;i<128;++i){char key[12];snprintf(key,sizeof(key),"id%u",i);size_t size=sizeof(state.slots[i].id);auto read=nvs_get_str(legacy,key,state.slots[i].id,&size);if(read!=ESP_OK&&read!=ESP_ERR_NVS_NOT_FOUND){state.version=0;break;}}
 int64_t cycle=0;result=nvs_get_i64(legacy,"cycle_at",&cycle);if(result==ESP_OK)state.cycle_at=cycle;else if(result!=ESP_ERR_NVS_NOT_FOUND)state.version=0;
 nvs_close(legacy);return state;
}
static bool save_journal(const JournalState& state){size_t used=0;for(size_t i=0;i<state.slots.size();++i)if(state.slots[i].id[0])used=i+1;size_t length=offsetof(JournalState,slots)+used*sizeof(JournalSlot);return journal_handle&&nvs_set_blob(journal_handle,"state",&state,length)==ESP_OK&&nvs_commit(journal_handle)==ESP_OK;}
struct EventCheckpoint {uint32_t version=1,count=0;char messages[32][768]={};};
static bool event_storage_valid=false;
static std::deque<std::string> load_events(){
 std::deque<std::string> result;
 if(nvs_flash_init_partition("events")!=ESP_OK||nvs_open_from_partition("events","outbox",NVS_READWRITE,&event_handle)!=ESP_OK)return result;
 static EventCheckpoint state;size_t length=sizeof(state);auto read=nvs_get_blob(event_handle,"pending",&state,&length);
 if(read==ESP_ERR_NVS_NOT_FOUND){event_storage_valid=true;return result;}
 if(read!=ESP_OK||length<offsetof(EventCheckpoint,messages)||state.version!=1||state.count>32)return result;
 size_t used=offsetof(EventCheckpoint,messages)+state.count*sizeof(state.messages[0]);
 if(length!=used&&length!=sizeof(state))return result; // Accept full legacy snapshot or compact prefix.
 for(unsigned i=0;i<state.count;++i){if(!memchr(state.messages[i],0,sizeof(state.messages[i])))return {};result.emplace_back(state.messages[i]);}
 event_storage_valid=true;return result;
}
static bool save_events(const std::deque<std::string>& pending){
 if(!event_handle||pending.size()>32)return false;
 static EventCheckpoint state;memset(state.messages,0,sizeof(state.messages));state.version=1;state.count=pending.size();
 for(unsigned i=0;i<state.count;++i){if(pending[i].size()>=sizeof(state.messages[i]))return false;memcpy(state.messages[i],pending[i].c_str(),pending[i].size()+1);}
 size_t used=offsetof(EventCheckpoint,messages)+state.count*sizeof(state.messages[0]);
 return nvs_set_blob(event_handle,"pending",&state,used)==ESP_OK&&nvs_commit(event_handle)==ESP_OK;
}
static SharedRig* controller=nullptr;
static esp_mqtt_client_handle_t mqtt=nullptr;
static std::string device,broker,username,password,ca,ssid,wifi_password,ntp,experiment;
static std::array<UnitIdentity,3> units={UnitIdentity{"","T1"},UnitIdentity{"","T2"},UnitIdentity{"","T3"}};
struct Message {std::string topic,payload;};
static Buffer<Message> outbox(32);
static DurableBuffer* durable_events=nullptr;
static std::array<Sensors,3> sensors; // Invalid by default; no fabricated physical measurements.
static double shared_removed_ml=0;
static bool connected=false;
static bool subscribed=false;
static std::atomic<bool> utc_synced{false};
static void clock_synced(timeval*){utc_synced.store(true);}
static int in_flight=-1;
static bool in_flight_event=false;
static int early_ack=-1;
static int early_deleted=-1;
static bool persist_event(size_t,const Event&);
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
static void acknowledge_message(){
 if(in_flight_event){if(!durable_events->acknowledged())controller->watchdog(epoch());}
 else outbox.acknowledged();
 in_flight=-1;
}
static void mqtt_event(void*,esp_event_base_t,int32_t id,void*data){
 xSemaphoreTake(mutex,portMAX_DELAY);
 auto e=static_cast<esp_mqtt_event_handle_t>(data);
 if(id==MQTT_EVENT_CONNECTED){connected=true;controller->connectivity(true);esp_mqtt_client_subscribe(mqtt,("irrigation/v1/"+device+"/commands").c_str(),1);
  // Main loop opens the remote barrier only after subscription/clock/backlog checks.
 }else if(id==MQTT_EVENT_DISCONNECTED){connected=false;subscribed=false;controller->connectivity(false);}
 else if(id==MQTT_EVENT_SUBSCRIBED){subscribed=true;}
 else if(id==MQTT_EVENT_PUBLISHED){if(in_flight==-2)early_ack=e->msg_id;else if(e->msg_id==in_flight)acknowledge_message();}
 else if(id==MQTT_EVENT_DELETED){if(in_flight==-2)early_deleted=e->msg_id;else if(e->msg_id==in_flight)in_flight=-1;}
 else if(id==MQTT_EVENT_DATA){
  if(e->total_data_len!=e->data_len||e->current_data_offset||e->data_len>2048){xSemaphoreGive(mutex);return;}
  if(std::string(e->topic,e->topic_len)!="irrigation/v1/"+device+"/commands"){xSemaphoreGive(mutex);return;}
  auto j=cJSON_ParseWithLength(e->data,e->data_len);if(!j){xSemaphoreGive(mutex);return;}
  auto cid=str(j,"command_id"),dev=str(j,"device_id"),source=str(j,"source");
  auto experiment=str(j,"experiment_id"),unit=str(j,"unit_id"),treatment=str(j,"treatment"),reason=str(j,"reason");
  if(valid_uuid(cid)&&dev&&source&&experiment&&unit&&treatment&&reason&&device==dev&&::experiment==experiment&&num(j,"schema_version")==1&&!strcmp(source,::source())){
   Command c{cid,iso(str(j,"issued_at")),iso(str(j,"expires_at")),num(j,"target_volume_ml"),num(j,"max_duration_s")};
   for(size_t i=0;i<3;++i)if(units[i].unit_id==unit){
    if(units[i].treatment!=treatment)persist_event(i,{cid,"rejected","unit_treatment_mismatch",false});
    else if(c.expires_at-c.issued_at<=300&&c.duration_s<=300)controller->submit(i,c,sensors[i],epoch());
    break;
   }
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
static bool persist_event(size_t channel,const Event&e){
  if(!durable_events)return false;
  auto j=cJSON_CreateObject();cJSON_AddNumberToObject(j,"schema_version",1);
  auto eid=uuid();cJSON_AddStringToObject(j,"event_id",eid.c_str());
  cJSON_AddStringToObject(j,"command_id",e.command_id.c_str());cJSON_AddStringToObject(j,"device_id",device.c_str());
  cJSON_AddStringToObject(j,"source",source());auto stamp=event_stamp();
  cJSON_AddStringToObject(j,"origin",e.local?"local":"remote");
  cJSON_AddStringToObject(j,"experiment_id",experiment.c_str());cJSON_AddStringToObject(j,"unit_id",units[channel].unit_id.c_str());cJSON_AddStringToObject(j,"treatment",units[channel].treatment.c_str());
  cJSON_AddBoolToObject(j,"measurements_valid",false);
  cJSON_AddStringToObject(j,"occurred_at",stamp.c_str());cJSON_AddStringToObject(j,"status",e.status.c_str());cJSON_AddStringToObject(j,"reason",e.reason.c_str());
  char*s=cJSON_PrintUnformatted(j);bool saved=s&&durable_events->push_cycle(s,e.status);if(s)free(s);cJSON_Delete(j);
  return saved;
}
static void queue_synthetic_telemetry(size_t channel){
#if CONFIG_IRRIGATION_SIMULATION
 const auto& sensor=sensors[channel];const auto& identity=units[channel];
 auto j=cJSON_CreateObject();cJSON_AddNumberToObject(j,"schema_version",1);
 auto id=uuid();cJSON_AddStringToObject(j,"message_id",id.c_str());
 cJSON_AddStringToObject(j,"device_id",device.c_str());cJSON_AddStringToObject(j,"experiment_id",experiment.c_str());cJSON_AddStringToObject(j,"unit_id",identity.unit_id.c_str());
 cJSON_AddStringToObject(j,"treatment",identity.treatment.c_str());cJSON_AddStringToObject(j,"source","simulation");
 char stamp[32];time_t now=time(nullptr);tm utc;gmtime_r(&now,&utc);strftime(stamp,sizeof(stamp),"%Y-%m-%dT%H:%M:%SZ",&utc);cJSON_AddStringToObject(j,"collected_at",stamp);
 auto calibration="sim-fixture-"+identity.unit_id;cJSON_AddStringToObject(j,"calibration_id",calibration.c_str());cJSON_AddNumberToObject(j,"soil_raw",2000);cJSON_AddNumberToObject(j,"soil_index",sensor.soil);cJSON_AddBoolToObject(j,"sensor_valid",sensor.valid);
 cJSON_AddNumberToObject(j,"temperature_c",23);cJSON_AddNumberToObject(j,"humidity_pct",50);cJSON_AddNumberToObject(j,"reservoir_mass_g",sensor.available_ml);
 char*s=cJSON_PrintUnformatted(j);if(s){outbox.push({"irrigation/v1/"+device+"/telemetry",s});free(s);}cJSON_Delete(j);
#endif
 (void)channel;
}
extern "C" void app_main(){
 pump.off_all(); // First application action; physical driver intentionally absent.
 setenv("TZ","UTC0",1);tzset();
 if(nvs_flash_init()!=ESP_OK){ESP_LOGE(TAG,"NVS unavailable; locked off");return;}
 static RetainedJournal journal(load_journal(),save_journal);
 auto restored=load_events();static DurableBuffer event_buffer(32,std::move(restored),save_events,event_storage_valid);durable_events=&event_buffer;
 mutex=xSemaphoreCreateMutex();
 nvs_handle_t settings;
 if(nvs_flash_init_partition("provision")==ESP_OK&&nvs_open_from_partition("provision","settings",NVS_READONLY,&settings)==ESP_OK){
  device=get(settings,"device");broker=get(settings,"broker");username=get(settings,"username");password=get(settings,"password");ca=get(settings,"ca");ssid=get(settings,"ssid");wifi_password=get(settings,"wifi_password");ntp=get(settings,"ntp");experiment=get(settings,"experiment");
  units[0].unit_id=get(settings,"unit1");if(units[0].unit_id.empty())units[0].unit_id=get(settings,"unit");units[1].unit_id=get(settings,"unit2");units[2].unit_id=get(settings,"unit3");nvs_close(settings);
 }
 if(units[0].unit_id.empty()||units[1].unit_id.empty()||units[2].unit_id.empty()||units[0].unit_id==units[1].unit_id||units[0].unit_id==units[2].unit_id||units[1].unit_id==units[2].unit_id){ESP_LOGE(TAG,"Configure three distinct units; locked off");return;}
 Limits limits{};
#if CONFIG_IRRIGATION_SIMULATION
 // Explicit synthetic fixture limits, never physical calibration.
 if(device.rfind("sim-",0)!=0||experiment.rfind("sim-",0)!=0){ESP_LOGE(TAG,"Simulation requires sim- identities");return;}
 limits=Limits{true,50,10,30,60,20,5};
#endif
 static SharedRig core(units,limits,journal,pump,uuid,persist_event,20,2);controller=&core;
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
  std::string publish_topic,publish_payload;
  xSemaphoreTake(mutex,portMAX_DELAY);
#if CONFIG_IRRIGATION_SIMULATION
  if(utc_synced.load())controller->advance(epoch());
  if(pump.channel>=0){shared_removed_ml+=1;auto&s=sensors[pump.channel];s.soil=s.soil<99?s.soil+1:100;} // Synthetic flow/response only.
  for(size_t i=0;i<3;++i){auto&s=sensors[i];if(!s.sampled_at)s.soil=40;else s.soil=s.soil>0.001?s.soil-0.001:0;s.valid=utc_synced.load();s.available_ml=shared_removed_ml<1000?1000-shared_removed_ml:0;s.removed_ml=shared_removed_ml;s.sampled_at=epoch();s.mass_stable=controller->stable();}
#endif
  if(utc_synced.load())controller->tick(sensors,epoch());
  if(utc_synced.load()&&epoch()>1700000000&&epoch()-last_telemetry>=5){for(size_t i=0;i<3;++i)queue_synthetic_telemetry(i);last_telemetry=epoch();}
  if(connected&&subscribed&&utc_synced.load()&&epoch()>1700000000&&outbox.size()==0&&durable_events->size()==0&&in_flight==-1&&!controller->running())controller->synchronize(epoch());
  // PUBACK only releases the delivery buffer; it never proves physical actuation.
  if(connected&&in_flight==-1){
   if(durable_events->front()){publish_topic="irrigation/v1/"+device+"/events";publish_payload=*durable_events->front();in_flight_event=true;}
   else if(outbox.front()){publish_topic=outbox.front()->topic;publish_payload=outbox.front()->payload;in_flight_event=false;}
   if(!publish_payload.empty()){in_flight=-2;early_ack=-1;early_deleted=-1;}
  }
  if(outbox.dropped!=reported_dropped){ESP_LOGW(TAG,"Outbound overflow: %u messages lost",static_cast<unsigned>(outbox.dropped));reported_dropped=outbox.dropped;}
  xSemaphoreGive(mutex);
  // Do not hold the controller mutex while acquiring the MQTT library API mutex.
  if(!publish_payload.empty()){
   int message=esp_mqtt_client_publish(mqtt,publish_topic.c_str(),publish_payload.c_str(),0,1,0);
   xSemaphoreTake(mutex,portMAX_DELAY);in_flight=message;
   if(message>=0&&early_ack==message)acknowledge_message();else if(message>=0&&early_deleted==message)in_flight=-1;
   xSemaphoreGive(mutex);
  }
  esp_task_wdt_reset();vTaskDelay(pdMS_TO_TICKS(100));}
}
