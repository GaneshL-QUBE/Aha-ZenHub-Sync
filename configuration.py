import os
import sys
import json
from objectifier import Objectifier

global_configuration = '''{
    "Zenhub_Domain":"https://api.zenhub.io",
    "Aha_Domain":"https://qubecinema.aha.io",
    "Zenhub_repo_Id":"142958202",
    "product_id":"6621690727465297561",
    "product_ref":"QW",
    "repo_name":"Realimage/qube-wire",
    "update_release_dates": false,
    "Track_due_date": true,
    "Owner":"dhanya@qubecinema.com",
    "features_source_of_release_date": "github",
    "AHA_TOKEN":"Bearer aha token",
    "ZENHUB_TOKEN":"zenhub token",
    "GITHUB_TOKEN":"github token",
    "slack_channel":"UL883UDND",
    "purgeEntries": true,
    "ahaReleaseTheme": "<p><a href='https://app.zenhub.com/workspaces/qube-wire-5b5fddaf99e4fb625b6974ce/reports/release?release={0}'>ZenhubLink</a></p>",
    "ahaEpicLink":"<p><a href='https://app.zenhub.com/workspaces/qube-wire-5b5fddaf99e4fb625b6974ce/issues/realimage/qube-wire/{0}'>Zenhub_Link</a></p>",
    "default_pipeline_id": "5cd9373451ea4a02378d71c3",
    "workspace_id":"5b5fddaf99e4fb625b6974ce"
}'''



def getConfiguration():
   
    config= json.loads(global_configuration)
    config=Objectifier(config)
    env_config = json.loads(os.environ.get(sys.argv[1]))
    env_config = Objectifier(env_config)
    config = {**config, **env_config}
    return config