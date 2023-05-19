from fastapi import FastAPI,HTTPException,Request
from bson import ObjectId
import motor.motor_asyncio
from fastapi.middleware.cors import CORSMiddleware
import pydantic
import os
from dotenv import load_dotenv
from datetime import datetime,timedelta
import uvicorn
import json
import requests
import pytz
import re

referencetemp=28.0

app = FastAPI()

#FastAPI (Uvicorn) runs on 8000 by Default


load_dotenv() #Nile Code, loads things from the coding environment
client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv('MONGO_CONNECTION_STRING'))#Attempt at hiding URL - Nile
db = client.statedb
db2 = client.settingsdb

pydantic.json.ENCODERS_BY_TYPE[ObjectId]=str

origins = ["https://simple-smart-hub-client.netlify.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#POST Because we actually want a record of the previous ones  
@app.post("/api/state",status_code=201) #cool that I changed it to post ?
async def set_state(request:Request):
    
    state = await request.json()
    state["datetime"]=datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    new_state = await db["states"].insert_one(state)
    updated_state = await db["states"].find_one({"_id": new_state.inserted_id }) #updated_tank.upserted_id
    if new_state.acknowledged == True:
        return updated_state
    raise HTTPException(status_code=400,detail="Issue")

#GET /data
@app.get("/api/state")
async def getstate():

    currentstate = await db["states"].find().to_list(1)
    currentsettings = await db["settings"].find().to_list(1)

    fanstate = ((float(currentstate[0]["temperature"])>float(currentsettings[0]["user_temp"])) and (currentstate[0]["presence"]))  #Watch Formatting here

    timenow=datetime.strptime(datetime.strftime(datetime.now(),'%H:%M:%S'),'%H:%M:%S')
    userlight=datetime.strptime(currentsettings[0]["user_light"],'%H:%M:%S')
    lightoff=datetime.strptime(currentsettings[0]["light_time_off"],'%H:%M:%S')

    lightstate = (timenow>userlight) and ((currentstate[0]["presence"])) and (timenow<lightoff)
    #Print Statements for Debugging
    print(datetime.strftime(datetime.now(),'%H:%M:%S'))
    print(currentsettings[0]["user_light"])
    print(currentsettings[0]["light_time_off"])

    Dictionary ={"fan":fanstate, "light":lightstate}
    return Dictionary

def sunset():
    sunsetresponse=requests.get(f'https://api.sunrise-sunset.org/json?lat=18.1096&lng=-77.2975&date=today')
    sunsetjson = sunsetresponse.json()
    sunsettimedate = sunsetjson["results"]["sunset"] #Returns Sunset in UTC Time
    sunsettimedate = datetime.strptime(sunsettimedate,'%I:%M:%S %p') + timedelta(hours=-5) #Converting form UTC to GMT-5 (Our Timezone)
    sunsettimedate = datetime.strftime(sunsettimedate,'%H:%M:%S') 
    return sunsettimedate

#GET /Graph
@app.get("/graph", status_code=200)
async def graphpoints(request:Request,size: int):
    n = size
    statearray = await db["states"].find().to_list(n)
    return statearray


#PUT /Settings
@app.put("/settings",status_code=200)
async def setting(request:Request):
    
    setting = await request.json()
    elements = await db["settings"].find().to_list(1)
    mod_setting = {}
    mod_setting["user_temp"]=setting["user_temp"]
    if setting["user_light"]== "sunset":
        mod_setting["user_light"]=sunset()
    else:
        mod_setting["user_light"] = setting["user_light"]
    
    mod_setting["light_time_off"]= (datetime.strptime(mod_setting["user_light"],'%H:%M:%S')+parse_time(setting["light_duration"])).strftime("%H:%M:%S") #Convert to string ?
    

    if len(elements)==0:
         new_setting = await db["settings"].insert_one(mod_setting)
         patched_setting = await db["settings"].find_one({"_id": new_setting.inserted_id }) #updated_tank.upserted_id
         return patched_setting
    else:
        id=elements[0]["_id"]
        updated_setting= await db["settings"].update_one({"_id":id},{"$set": mod_setting})
        patched_setting = await db["settings"].find_one({"_id": id}) #updated_tank.upserted_id
        if updated_setting.modified_count>=1: 
            return patched_setting
    raise HTTPException(status_code=400,detail="Issue")


regex = re.compile(r'((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_time(time_str):
    parts = regex.match(time_str)
    if not parts:
        return
    parts = parts.groupdict()
    time_params = {}
    for name, param in parts.items():
        if param:
            time_params[name] = int(param)
    return timedelta(**time_params)

