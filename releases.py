import requests
from urllib.parse import urljoin
import json
import sys,os
from objectifier import Objectifier
import logging
import release_templates
from configuration import getConfiguration
import aha_zen_master_feature_importer as azf

config = getConfiguration()

AHA_TOKEN=config.AHA_TOKEN
ZENHUB_TOKEN=config.ZENHUB_TOKEN
AHA_HEADER={'Authorization':AHA_TOKEN,'Content-Type': "application/json","User-Agent":"praveentechnic@gmail.com"}
ZENHUB_HEADER={'X-Authentication-Token':ZENHUB_TOKEN}
GITHUB_TOKEN=config.GITHUB_TOKEN
global aha_releases_names
global aha_releases_name_map 
global Releases_in_Aha 
global Releases_in_Zenhub 

logging.basicConfig(level=logging.INFO,
 format="%(levelname)s:%(filename)s,%(lineno)d:%(name)s.%(funcName)s:%(message)s", 
  handlers=[logging.StreamHandler()])
logger=logging.getLogger()



#Get all the releases from Zenhub

def getReleasesFromZenhub(repoid):
    url=urljoin(config.Zenhub_Domain,'/p1/repositories/{0}/reports/releases'.format(str(repoid)))
    rs= requests.get(url=url, headers=ZENHUB_HEADER)
    if(rs.status_code==200):
        return rs.json()
    else:
        return None

#Get All Releases from Aha!

def getReleasesfromAha(page=1):
    data={"releases":[]}
    url=urljoin(config.Aha_Domain,'/api/v1/products/{product_id}/releases'.format(product_id=config.product_id))
    rs= requests.get(url, headers=AHA_HEADER,params={"page":page})
    if(rs.status_code==200):
        data["releases"]=data["releases"]+rs.json()['releases']
        currentpage=rs.json()['pagination']['current_page']
        total_pages=rs.json()['pagination']['total_pages']
        if(total_pages>currentpage):
            data["releases"]=data["releases"]+getReleasesfromAha(page=currentpage+1)['releases']
    else:
        return None
    return data



#Create a Release on Aha!
def createReleaseOnAha( name , release_date, workflow_status,owner="dhanya@qubecinema.com"):
    url=urljoin(config.Aha_Domain,'/api/v1/products/{product_id}/releases'.format(product_id=config.product_id))
    data={
        "release":{
            "owner":owner,
            "name":name,
            "release_date":release_date,
            "workflow_status":workflow_status
        }
    }
    rs=requests.post(url=url, json=data, headers= AHA_HEADER)
    if(rs.status_code==200):
        return rs.json()
    else:
        return {'state':'FAILED', 'status_code': rs.status_code , 'response':rs.text()}


#Udpate a Release on Aha!

def updateReleaseOnAha(id, name, release_date, workflow_status):
    url=urljoin(config.Aha_Domain,'/api/v1/products/{product_id}/releases/{id}'.format(product_id=config.product_id, id= id))
    data={
        "release":{            
            
        }
    }
    if(name is not None):
        data['release']['name']=name
    if(release_date is not None):
        data['release']['release_date']=release_date
    if(workflow_status is not None):
        data['release']['workflow_status']=workflow_status

    rs=requests.put(url, json=data, headers=AHA_HEADER)
    if(rs.status_code==200):
        return rs.json()
    else:
        return {'state':'FAILED', 'status_code': rs.status_code , 'response':rs.text()}

#generatediff
def generatediff(ZH_Release, Aha_Release):
    changes={"name":None, "release_date":None, "workflow_status":None }
    if(ZH_Release['title'] != Aha_Release['release']['name']):
        changes['name']=ZH_Release['title']
    if(ZH_Release['desired_end_date'].split('T')[0] != Aha_Release['release']['release_date'] ):
        changes['release_date']=ZH_Release['desired_end_date'].split('T')[0]
    status=ZH_Release['state']
    if(status=='open'):
        status='Backlog'
    if(status=='closed'):
        status='Released'
    if(status!=Aha_Release['release']['workflow_status']['name']):
        changes['workflow_status']=status

    return changes

def getAhaReleasebyId(id):
    url=urljoin(config.Aha_Domain,'/api/v1/releases/{0}'.format(id))
    rs=requests.get(url=url, headers=AHA_HEADER)
    if(rs.status_code==200):
        return rs.json()
    else:
        return None

def getZHReleasebyID(AllReleases, id):
    for items in AllReleases:
        if(items['release_id']==id):
            return items
    return None

#Get Translation data
def getTranslationData(jsoncontent,key):
    try:
        return jsoncontent[key]
    except KeyError:
        logging.error("The requested translation data {0} is not found on the map".format(key))
        return None

def create_release_phase(data):
    url=urljoin(config.Aha_Domain,'/api/v1/release_phases')
    rs= requests.post(url, headers=AHA_HEADER , json = data)
    if(rs.status_code==200):
        #logger.info("Created Release phase for")
        return rs.json()
    else:
        return None

#Add Release Templates to the Created releases
def add_Release_Templates(response):
    ID = response['release']['id']
    start_date = response['release']['start_date']
    end_date = response['release']['release_date']
    template = release_templates.get_release_templates(ID,start_date,end_date)
    for items in template:
        create_release_phase(items)

def deleteAhaRelease(release):
    ID = release['id']
    url = urljoin(config.Aha_Domain, '/api/v1/products/{product_id}/releases/{id}'.format(product_id=config.product_id,id=ID))
    rs = requests.delete(url, headers=AHA_HEADER)
    if (rs.status_code == 204):
        logger.info("Release deleted successfully {0}".format(release['name']))
    else:
        logger.error("Release deletion failed for  {0} with response {1}".format(release['name'], rs.json()))


def fillAhaReleaseNames():
    global Releases_in_Aha
    global aha_releases_name_map
    global aha_releases_names

    for release in Releases_in_Aha['releases']:
        #print("Release here:"+str(release['name']))
        aha_releases_name_map[release['name']] = release['id']
        aha_releases_names.append(release['name'])


def createNewReleaseForAha(name, release):
    logger.info("Inserting following Release to Aha" + name)
    release_date_to_be_updated_to_AHA= release['desired_end_date'].split('T')[0]
    status=release['state']
    if(status=='open'):
        status='Backlog'
    if(status=='closed'):
        status='Released'
    creation=createReleaseOnAha(name=name, release_date = release_date_to_be_updated_to_AHA, workflow_status=status)
    if('state' not in creation.keys()):
        add_Release_Templates(creation)
        print("Created new Release on Aha! {0}".format(creation['release']['reference_num']))
        #endurance[release['release_id']]={"aha_ref_num":creation['release']['reference_num'], "aha_release_id": creation['release']['id']}
        aha_releases_names.append(name)
        aha_releases_name_map[name] = creation['release']['id']

def exceptionHandler(data):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    logger.error("{0} {1} {2} {3}".format(data, exc_type, fname, exc_tb.tb_lineno))

#Get all issues for release
def getAllIssuesForRelease(release):
    url = urljoin(config.Zenhub_Domain, '/p1/reports/release/{release_id}/issues'.format(release_id=release['release_id']))
    rs = requests.get(url, headers=ZENHUB_HEADER)
    if (rs.status_code == 200):
        result = rs.json()
        return result
    else:
        loggger.ERROR("Error getting all issues for a zenhub release {0}".format(release['title']))

#Get Details of an issue from Zenhub
def getIssueDetailFromZen(issue_id):
    rs= requests.get(url= urljoin(config.Zenhub_Domain,'/p1/repositories/{0}/issues/{1}'.format(str(config.Zenhub_repo_Id),str(issue_id))),headers=ZENHUB_HEADER)
    if(rs.status_code==200):
        result= rs.json()
        result['id']=issue_id
        return result
    else:
        #Log error
        logger.error("Error getting zenhub issue or id:{0}".format(issue_id))
        return None

def getAllMasterFeaturesFromAha(page=1):
    data = []
    url = urljoin(config.Aha_Domain, '/api/v1/products/{product_id}/master_features'.format(product_id=config.product_id))
    rs = requests.get(url, headers=AHA_HEADER)
    if (rs.status_code == 200):
        data += rs.json()['master_features']
        currentpage=rs.json()['pagination']['current_page']
        total_pages=rs.json()['pagination']['total_pages']
        if(total_pages>currentpage):
            data += getReleasesfromAha(page=currentpage+1)
        return data
    else:
        logger.error("Error getting all the master features from AHA")
        raise NotImplementedError("Cannot handle without purge")


def deleteAhaMasterFeature(master_feature):
    ID = master_feature['id']
    url = urljoin(config.Aha_Domain, '/api/v1/master_features/{id}'.format(id=ID))
    rs = requests.delete(url, headers=AHA_HEADER)
    if (rs.status_code == 204):
        logger.info("Master Feature deleted successfully {0}".format(master_feature['name']))
    else:
        logger.error("Master Feature deletion failed for  {0} with response {1}".format(master_feature['name'], rs.json()))

def main():
    global aha_releases_names
    global aha_releases_name_map
    global Releases_in_Aha 
    global Releases_in_Zenhub 

    Releases_in_Zenhub= getReleasesFromZenhub(config.Zenhub_repo_Id)
    Releases_in_Aha= getReleasesfromAha()
    
    #print("Releases in Zenhub"+str(Releases_in_Zenhub))
    #print("Releases in Aha"+str(Releases_in_Aha))

    #Purging Existing Releases
    if (config.purgeEntries):
        master_features = getAllMasterFeaturesFromAha()
        logger.info("Master Features Found : {0}".format(len(master_features)))
        for master_feature in master_features:
            deleteAhaMasterFeature(master_feature)

        print("Purging Existing releases in Aha {0}".format(len(Releases_in_Aha['releases'])))
        for release in Releases_in_Aha['releases']:
            deleteAhaRelease(release)
        Releases_in_Aha= getReleasesfromAha() #Get the fresh list from Aha Again

       

     
    aha_releases_names = []
    aha_releases_name_map = {}
    fillAhaReleaseNames()

    print("Aha Release Names Before Sync:"+str(aha_releases_names))
    try:
        for release in Releases_in_Zenhub:
            
            name = release['title']
            if(name not in aha_releases_names): #Data is not available in endurance, So we are creating a new release , 2 Level Check 
                try:
                    createNewReleaseForAha(name, release)
                    
                except Exception as e:
                    exceptionHandler("Error in creating Release {0} as exception {1}".format(name, e))    
                
            else:# data is available, so we will check for updates
                print("Zenhub release found in Aha:" + name)

    except Exception as e:
        exceptionHandler("Release Syncer Exception")
    finally:
        #This will update the final result for all further processing.
        Releases_in_Aha = getReleasesfromAha()
        fillAhaReleaseNames()

    syncEpicsFromZenToAha()


#Create a new master feature on Aha
def insertMasterFeatureAha(zenhub_issue, zehub_issue_number, aha_release_id):    
    git_repo=azf.github_object(azf.GITHUB_TOKEN,config.repo_name)
    issue = git_repo.issue(zehub_issue_number)

    #TODO: Make this better. 
    name=issue.title
    description=issue.body + "[Zenhub_Link:https://app.zenhub.com/workspaces/qube-wire-5b5fddaf99e4fb625b6974ce/issues/realimage/qube-wire/"+str(zehub_issue_number)
    try:
        status=getTranslationData(json.load(open('zen2ahaMap.json')),zenhub_issue['pipeline']['name'])            
    except:
        status="Backlog"

    if(status is "Released"):
        return None
        

    model={
  "master_feature": {
    "name": name,
    "description": description,    
    "workflow_status": {            
            "name": status
        }
            }
            }

    rs=requests.post(url= urljoin(config.Aha_Domain ,'api/v1/releases/{release_id}/master_features'.format(release_id=aha_release_id)),data=json.dumps(model), headers=AHA_HEADER)
    return rs


def syncEpicsFromZenToAha():
    try:
        for zenHubRelease in Releases_in_Zenhub:
            try:
                
                if (zenHubRelease['title'] not in aha_releases_names):
                    logger.error("Not Syncing any issues in this release: {0}".format(zenHubRelease['title']))
                    continue

                aha_release_id = aha_releases_name_map[zenHubRelease['title']]
                issues = getAllIssuesForRelease(zenHubRelease)
                logger.info("Issues {0} for release {1}".format(issues, zenHubRelease['title']))
                for issue in issues:

                    try:
                        zenhub_issue = getIssueDetailFromZen(issue_id=issue['issue_number'])
                    
                        if (zenhub_issue["is_epic"]):
                            
                            response=insertMasterFeatureAha(zenhub_issue, issue['issue_number'], aha_release_id)
                            logger.info("zenhub issue : {0}".format(zenhub_issue))
                        else:
                            #reponse=insertStoryToAha(issue['issue_number'], aha_release_id)
                            continue

                    except Exception as identifier:
                        exceptionHandler("Error in syncing epic {0} with following exception {1} ".format(issue['issue_number'], identifier))
                   
                    
                    #TODO: See if it is already present in Aha.
                    
            except Exception as identifier:
                exceptionHandler("Error in syncing Release {0} with following exception {1} ".format(zenHubRelease['title'], identifier))

    except Exception as identifier:
        exceptionHandler("Exception in syncing Issues {0}".format(identifier))
    finally:
        pass



