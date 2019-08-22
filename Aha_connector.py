from urllib.parse import urljoin
import requests
import json

import logging

logger = logging.getLogger("root")

class AhaConnector:
    def __init__(self, config):
        self.config = config
        self.AHA_HEADER={'Authorization':config.AHA_TOKEN,'Content-Type': "application/json","User-Agent":"ganesh.l@qubecinema.com"}
        self.AHA_UPDATE_HEADER = self.AHA_HEADER
        self.AHA_UPDATE_HEADER["Accept"] = "application/json"
        self.releases = self.__getReleasesfromAha()
        self.releasesMap = {}
        self.openReleasesMap = {}
        self.releasesNameMap = {}

        self.mappedAhaZenhubReleases={}
        self.mappedZenhubAhaReleases={}
        self.unmappedAhaReleases=[] #TODO:deprecate this

        self.epicsMap = {}

        self.mappedAhaZenhubEpics={}
        self.mappedZenhubAhaEpics={}


        self.releaseAndEpicsMap={}

        

        self.__processReleasesFromAha()
        self.__processEpicsFromAha()

    def getReleases(self):
        return self.releases


    def __processReleasesFromAha(self):
        releases = self.__getReleasesfromAha()

        for release in releases:
            logger.info("Loading Release : {0} ".format(release['name']))
            releaseData = self.__getReleaseFromAha(release["resource"])['release']


            if releaseData['name'] == "Parking Lot":
                #Do not process Parking Lot Release. 
                #It is a special type of release in Aha to park epics and features
                continue
            
            ahaId = releaseData["id"]
            zenhubId = None
            self.releasesMap[ahaId] = releaseData

            if not releaseData["released"]:
                self.openReleasesMap[ahaId] = releaseData

        
            try:
                #Trying to match zenhub and aha directly by using the theme field with appropriate string checks
                if not releaseData["theme"] == "" and not releaseData["theme"]["body"] == "":
                    theme = releaseData["theme"]["body"]
                    string = theme.split('app.zenhub.com/workspaces/qube-wire-5b5fddaf99e4fb625b6974ce/reports/release?release=')
                    #logger.info("Testing output {0}".format(string))
                    string = string[1].split('">ZenhubLink</a>')
                    #logger.info("Testing output {0}".format(string))
                    zenhubId = string[0]
                    #logger.info("Zenhub Id Found for aha Release {0} is {1}".format(ahaId, zenhubId))
                    self.mappedAhaZenhubReleases[ahaId] = zenhubId
                    self.mappedZenhubAhaReleases[zenhubId] = ahaId
            except Exception as E:
                logger.warn("Error {1} mapping the theme to the zenhub link for release: {0} ".format(ahaId, E))
        
            #If the direct match fails, try a name check once. 
            if zenhubId is None:
                logger.warn("Zenhub Theme Mapping not found for the following umapped release: {0}".format(ahaId))
                self.releasesNameMap[releaseData["name"]] = ahaId


    def __getReleaseFromAha(self, url):
        response = requests.get(url, headers=self.AHA_HEADER)
        if (response.status_code == 200):
            return response.json()
        else:
            logger.error("Error getting Single Release data from Aha {0} of Release {1}".format(response, url))


    def __getReleasesfromAha(self, page=1):
        data=[]
        url=urljoin(self.config.Aha_Domain,'/api/v1/products/{product_id}/releases'.format(product_id=self.config.product_id))
        rs= requests.get(url, headers=self.AHA_HEADER,params={"page":page})
        if(rs.status_code==200):
            data += rs.json()['releases']
            currentpage=rs.json()['pagination']['current_page']
            total_pages=rs.json()['pagination']['total_pages']
            if(total_pages>currentpage):
                data += self.__getReleasesfromAha(page=currentpage+1)
        else:
            logger.error("Error getting Release data from Aha {0}".format(rs))
        return data

    def updateAhaReleaseTheme(self, ahaId, zenhubId):
        theme =  self.config.ahaReleaseTheme.format(zenhubId)
        #logger.info("theme: {0}".format(theme))
        url=urljoin(self.config.Aha_Domain,'/api/v1/releases/{ahaId}'.format(ahaId = ahaId))
        data={
            "release":{
                "theme": theme
            }
        }
        rs = requests.put(url, headers=self.AHA_UPDATE_HEADER, json=data)
        if rs.status_code == 200:
            return True
        else:
            logger.error("Error Updating Aha Theme : {0} For AhaId: {1}".format(rs, ahaId))


    def updateAhaRelease(self, ahaId, zenhubData):
        url=urljoin(self.config.Aha_Domain,'/api/v1/releases/{ahaId}'.format(ahaId = ahaId))

        release = {}
        if zenhubData['state'] == "closed":
            release["workflow_status"] = 'Released'
            release["release_date"] = zenhubData['closed_at'].split('T')[0]
        else:
            release["release_date"] = zenhubData['desired_end_date'].split('T')[0]
    
        data={
            "release":release
        }
        rs=requests.put(url=url, json=data, headers= self.AHA_UPDATE_HEADER)
        if(rs.status_code==200):
            return rs.json()
        else:
            logger.error("ZenhubData release update to Aha failed for : {0}".format(zenhubData['title']))




    #Get Epics from the Aha 
    def __getEpicsFromAha(self,page = 1):
        data=[]
        url=urljoin(self.config.Aha_Domain,'/api/v1/products/{product_id}/master_features'.format(product_id=self.config.product_id))
        rs= requests.get(url, headers=self.AHA_HEADER,params={"page":page})
        if(rs.status_code==200):
            data += rs.json()['master_features']
            currentpage=rs.json()['pagination']['current_page']
            total_pages=rs.json()['pagination']['total_pages']
            if(total_pages>currentpage):
                data += self.__getEpicsFromAha(page=currentpage+1)
        else:
            logger.error("Error getting Release data from Aha {0}".format(rs))
        return data


    def __getSingleEpicFromAha(self, url):
        response = requests.get(url, headers=self.AHA_HEADER)
        if (response.status_code == 200):
            return response.json()
        else:
            logger.error("Error getting Single Epic data from Aha {0} of Epic {1}".format(response, url))

    def updateZenhubEpicLinkToAha(self, ahaId, zenhubEpicNum):
        link =  self.config.ahaEpicLink.format(zenhubEpicNum)
        url=urljoin(self.config.Aha_Domain,'/api/v1/master_features/{ahaId}'.format(ahaId = ahaId))
        data={
            "description": link
        }
        rs = requests.put(url, headers=self.AHA_UPDATE_HEADER, json=data)
        if rs.status_code == 200:
            return True
        else:
            logger.error("Error Updating Zenhub Epic Link to Aha : {0} For AhaId: {1}".format(rs, ahaId))

    def __processEpicsFromAha(self):
        epics = self.__getEpicsFromAha()
        for epic in epics:
            logger.info("Loading Epic: {0}".format(epic["name"]))
            epicData = self.__getSingleEpicFromAha(url=epic["resource"])["master_feature"]
            ahaId = epicData["id"]
            self.epicsMap[ahaId] = epicData

            description = epicData["description"]["body"]

            releaseId = epicData["release"]["id"]
            try:
                self.releaseAndEpicsMap[releaseId].append(ahaId)
            except KeyError:
                self.releaseAndEpicsMap[releaseId] = [ahaId]


            try:
                #Trying to match zenhub and aha directly by using the link in the description that was added initially
                if description != "":
                    string = description.split('https://app.zenhub.com/workspaces/qube-wire-5b5fddaf99e4fb625b6974ce/issues/realimage/qube-wire/')
                    #logger.info("Testing output {0}".format(string))
                    string = string[1].split('\">Zenhub_Link')
                    #logger.info("Testing output {0}".format(string))
                    zenhubId = string[0]
                    #logger.info("Zenhub Id Found for aha Release {0} is {1}".format(ahaId, zenhubId))
                    self.mappedAhaZenhubEpics[ahaId] = zenhubId
                    self.mappedZenhubAhaEpics[zenhubId] = ahaId
                    
            except IndexError:
                logger.warn("Error finding right mapping to zenhub epic link to the aha epic: {0} - {1} ".format(epicData["name"], ahaId))
        
    def updateAhaEpic(self, ahaEpicId, zenhubData, ahaEpicData):
        if zenhubData is None:
            logger.error("Error in getting zenhub Data for ahaEpic: {0}".format(ahaEpicId))
            return

        #logger.info("{0}".format(zenhubData))

        try:
            zenhubStatus= zenhubData['pipeline']['name']
            status=self.__getTranslationData(json.load(open('zen2ahaMap.json')),zenhubStatus)
                
            model={  
                "workflow_status": {
                    "name": status
                }
            }
                    
            rs=requests.put(url= urljoin(self.config.Aha_Domain ,'api/v1/master_features/{epicId}'.format(epicId = ahaEpicId)),json=model, headers=self.AHA_UPDATE_HEADER)
            
            if rs.status_code == 200:
                logger.info("Successfully updated status for epic {0}".format(ahaEpicId))    
            else:
                logger.error("Error when updating zenhub status for aha Epic {0} : {1}".format(ahaEpicId, rs))     

        except KeyError:
            logger.error("Error updating Zenhub status for Zenhub issue {0}".format(zenhubData))


    #Get Translation data
    def __getTranslationData(self, jsoncontent, key):
        try:
            return jsoncontent[key]
        except KeyError:
            logger.error("The requested translation data '{0}' is not found on the map".format(key))
            return None


    #Update the Zenhub Link to Aha in description
    def updateAhaEpicLink(self, ahaEpicId, epicBody, zenhubId):
        url=urljoin(self.config.Aha_Domain,'/api/v1/master_features/{ahaId}'.format(ahaId = ahaEpicId))

        if epicBody is None:
            epicBody = ""


        data={
            "description": epicBody + self.config.ahaEpicLink.format(zenhubId)
        }
        rs = requests.put(url, headers=self.AHA_UPDATE_HEADER, json=data)
        if rs.status_code == 200:
            logger.info("Succesffully updated the description link for epic: {0}".format(ahaEpicId))
        else:
            logger.error("Error Updating Aha Epic Theme : {0} For AhaId: {1}".format(rs, ahaId))

    
    def getEpicsMapForRelease(self, releaseId):
        epicsMap = {}

        try:
            epicsList = self.releaseAndEpicsMap[releaseId]

            for epicId in epicsList:
                epicsMap[epicId] = self.epicsMap[epicId]
        
        except KeyError:
            logger.error("Release Id not found for epics Map: {0}".format(releaseId))
            
        return epicsMap

    
    
