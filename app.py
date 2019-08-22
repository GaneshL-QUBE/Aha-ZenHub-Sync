import slack_sender
from datetime import datetime
import sys
from objectifier import Objectifier
import json
import os
import requests
import releases
import aha_zen_adapter
import aha_zen_master_feature_importer

def upload_to_storage(data):
    domain = "https://qubewire-aha-integration.herokuapp.com"
    rs=requests.post(domain+'/insertresults', data= str(data)+ '     \n This Ran @ : '+str(datetime.now()))
    if(rs.status_code==200):
        return domain+'/getautomationresults?key='+str(rs.text)
        
    else:
        return ''


def main():
    config_selector= sys.argv[1]
    config= json.loads(os.environ.get(config_selector))
    os.environ['config']= os.environ.get(config_selector)
    print("Configuration loaded: " +os.environ['config'])
    config=Objectifier(config)
    
    release_updates = releases.main()
    slack_sender.send_message('Releases Sync happened @ '+str(datetime.now())+ ' logs @ ' +upload_to_storage(release_updates), config.slack_channel)

    #feature_update=aha_zen_adapter.main()
    #slack_sender.send_message('Features Sync happened @ '+str(datetime.now())+ ' logs @ ' +upload_to_storage(feature_update), config.slack_channel)
    
    #master_feature_update=aha_zen_master_feature_importer.main()
    #slack_sender.send_message('Master Features Sync happened @ '+str(datetime.now())+ ' logs @ ' +upload_to_storage(master_feature_update), config.slack_channel)

if __name__ == "__main__":
    main()