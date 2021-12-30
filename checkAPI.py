# Author: Igor Andrade
# HostGator LatAm - SysOps
# This script is used for get status of API's and send to zabbix + teams and google chat
# This also can be done with zabbix to manage the json and delivers the alerts, but i want also populate a database and use it inside grafana
# I can also delivers two types of alerts, since in my case its a sensitive alert, i will keep both, if the zabbix not works fine, this one can handle
# Date: 28/05/2021
#
# Updated: 29/12/2021
# - added the database population for grafana consume that data
# - added jinja2 as card for teams and gchat check attached file
#
# PS: Where you see a comment that starts with ##CHANGEME --> this means the Line below of it, should be changed.


from jinja2 import Environment, FileSystemLoader
import requests
import json
import urllib3
from httplib2 import Http
import subprocess   
import time
import MySQLdb as mysql
import os

###################################################
#                   VARS                          #
###################################################

try:
    import database as db
except: 
    print("Error! - Unable to load database config")

#. Function to insert informations in database .#
def update_database(table, state_is, time_now, id):

    #. Try connection and insert data in database .#
    try:

        connection = mysql.connect(db.host, db.user, db.password, db.database);

        cursor = connection.cursor()

        #cursor.execute("UPDATE " + table + " SET " +  "state_is = '" + state_is + "' AND time_now ='" + time_now + "' WHERE id = '" + id + "'" +  "VALUES ")
        cursor.execute("UPDATE " + table + " SET " +  "state_is = '" + state_is + "', time_now = \"" + time_now + "\" WHERE id = '" + id + "'")
        
        connection.commit()

        connection.close()

    #. Shows errors .#
    except Exception as e:
      
        print("Error ! " + str(e))
        os._exit(1)
##CHANGEME --> change the entire url to your URL
url = "https://url.healthchecks.io/healthcheck"

##CHANGEME --> Change the APIHERE
headers = {'x-api-key': 'APIHERE'}

#PATH where the template should be
file_loader = FileSystemLoader('.')

#load the enviroment of template
env = Environment(loader=file_loader)

def send_to_gchat(bot_message):
  ##CHANGEME --> change the "URL OF WEBHOOK GOOGLECHAT" and also change the "URL OF WEBHOOK TEAMS"
    url = ['URL OF WEBHOOK GOOGLECHAT', 'URL OF WEBHOOK TEAMS']
    for i in url:
        message_headers = { 'Content-Type': 'application/json; charset=UTF-8'}
##CHANGEME --> Replace ChangeMeHere for a name that contains in the teams url at line 69
        if 'ChangeMeHere' in i:
            payload = bot_message['teams']
        else:
            payload = bot_message['gsuite']

        http_obj = Http()

        response = http_obj.request(
            uri=i,
            method='POST',
            headers=message_headers,
            body=payload,
        )



# sending get request and saving the response as response object
response = requests.get(url=url, headers=headers)

# extracting data in json format
data = response.json()

# table, state_is, time_now, id
#print((data))
date_time = str(time.strftime("%d/%m/%Y - %H:%M"))
ate_time = str(time.strftime("%Y-%m-%d %H:%M:%S"))
##CHANGEME --> change for your URL Zabbix and that have your item ids for your event
urlzabbix = "https://yourzabbix.com/history.php?action=showvalues&itemids%5B%5D=1713367"

#apps ids for apis dict
##CHANGEME --> change the name for your service, that will used to populate the database
appids = { "paymentgateway1": "30", 
           "paymentgateway2": "40", 
           "paypal": "50" }


for i in data:
    if i['health_status'] == "OK": 
        print(f"API response of {i['service_name']} is fine")
        update_database('checker_last', "1", ate_time, appids[i['service_name']]);
    else:
        print(f"API response of {i['service_name']} is trouble")
        update_database('checker_last', "0", ate_time, appids[i['service_name']]);
        SendCardToGChat = {
          ##CHANGEME --> change the hostnameVAR value, for your hostname server that should alert
                "hostnameVAR": "serverthatwillhavescript.com.br",
                "DescriptionVAR": "endpoint of %s" % i['service_name'],
                "StatusVAR": "Trouble",
                "LastChangeVAR": date_time,
                "HappenedVAR": "now",
                "UrlGENERATEDVar": urlzabbix,
                    }
        
        template_gsuite = env.get_template('card.json')
        template_teams = env.get_template('card-teams.json')
        gsuite = template_gsuite.render(SendCardToGChat)
        teams = template_teams.render(SendCardToGChat)

        templates = {
            'teams': teams,
            'gsuite': gsuite
        }

        send_to_gchat(templates)
        ##CHANGEME --> change the URL of your zabbix and change the hostname for the server that will runs that script, also check the trigger name
        #if necessary change it.
        subprocess.run(['zabbix_sender', '-z', 'yourzabbix.com', '-s', 'serverthatwillhavescript.com.br', '-k', 'check_gateway_api.status', '-o', "1" ])
        print(SendCardToGChat)
