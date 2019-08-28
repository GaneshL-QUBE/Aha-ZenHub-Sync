import os
import json
from objectifier import Objectifier

global_configuration = '''{
    "Zenhub_Domain":"https://api.zenhub.io",
    "Aha_Domain":"https://qubecinema.aha.io",
    "Zenhub_repo_Id":"142958202",
    "product_id":"6727861953124899496",
    "product_ref":"QWI",
    "repo_name":"Realimage/qube-wire",
    "ndurance_key":"f952df70-3102-46ab-88c2-d3e383a5eeae",
    "update_release_dates": false,
    "Track_due_date": true,
    "Owner":"dhanya@qubecinema.com",
    "features_source_of_release_date": "github",
    "AHA_TOKEN":"Bearer 6c7f49bcd92d85d1117bf865db88242ee7089a37f6bee4dc306dca0885ca1c3c",
    "ZENHUB_TOKEN":"d5a1147e044dbd5087334b51a7f1695ac865681f4c5264d1448c81bea33c2d55bc6ec3191e417fb7",
    "GITHUB_TOKEN":"397dfd3ff8e52ba81b85cbe51f9d6f35cc8e05ee",
    "Endurance_Source":"https://endurance-qube.herokuapp.com/api/data_store/aha_zen_qubewire",
    "slack_channel":"UL883UDND",
    "Endurance_Source_3":"https://endurance-qube.herokuapp.com/api/data_store/aha_zen_qubewire_1",
    "purgeEntries": true
}'''

def getConfiguration():
    configuration = os.environ.get('config')
    if configuration is None:
        configuration = global_configuration
    config= json.loads(configuration)
    config=Objectifier(config)
    return config