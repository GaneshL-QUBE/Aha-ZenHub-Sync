from datetime import datetime
import sys
import json
import os
import log

#import requests

import configuration
import Aha_connector
import zenhub_connector

#import slack_sender
#import releases
#import aha_zen_adapter
#import aha_zen_master_feature_importer

logger = log.setup_custom_logger('root')


# def upload_to_storage(data):
#     domain = "https://qubewire-aha-integration.herokuapp.com"
#     rs=requests.post(domain+'/insertresults', data= str(data)+ '     \n This Ran @ : '+str(datetime.now()))
#     if(rs.status_code==200):
#         return domain+'/getautomationresults?key='+str(rs.text)
        
#     else:
#         return ''

mappedAhaZenhubReleases= {}
mappedZenhubAhaReleases={}


def main():
    config = configuration.getConfiguration()
    logger.info("Configuration loaded : {0}".format(configuration.global_configuration))

    Zenhub = zenhub_connector.ZenhubConnector(config)
    Aha = Aha_connector.AhaConnector(config)

    #data = Zenhub.github.get_issue(1777)
    #issue = Zenhub.github.get_issues()
    #logger.info("Data got for issue is {0}".format(data.is_closed))
    #raise NotImplementedError
    
    mapAhaZenhubReleases(Aha, Zenhub)
    #mapAhaZenhubEpics(Aha, Zenhub)
  

    logger.info("--------------Before the Sync starts: -------------------------")
    logger.info("No. of Releases in Aha: {0}".format(len(Aha.getReleases())))
    logger.info("No. of UnReleased Releases in Aha {0}".format(len(Aha.openReleasesMap)))
    logger.info("No. of Releases in Zenhub: {0}".format(len(Zenhub.releases)))
    logger.info("No. of Unmapped Releases {0}".format(len(Aha.unmappedAhaReleases)))
    logger.info("No. of Epics in Ahaq {0}".format(len(Aha.epicsMap)))

    # For Each UnReleased Release, sync all the zenhub / github update to the Release
    # If the Release is not found create it.
    CreateOrUpdateReleaseData(Aha, Zenhub)
    
    # for release in mappedAhaZenhubReleases:
    #     logger.info("Mapped Releases: {0}".format(release))

    # for release in unmappedAhaReleases:
    #     logger.info("Unmapped Aha Releases {0}".format(release))
    
    #Once the Releases are synced the Epics can be synced now. 
    #We Take all the Epics from Aha and sync it to zenhub.
    CreateOrUpdateEpicsData(Aha, Zenhub)





def mapAhaZenhubReleases(Aha, Zenhub):
    mappedAhaZenhubReleases = Aha.mappedAhaZenhubReleases
    mappedZenhubAhaReleases = Aha.mappedZenhubAhaReleases
    zenhubReleasesMap = Zenhub.releaseNamesMap

    for ahaReleaseName, ahaReleaseId in Aha.releasesNameMap.items():
        if ahaReleaseName in Zenhub.releaseNamesMap:
            mappedAhaZenhubReleases[ahaReleaseId] = zenhubReleasesMap[ahaReleaseName]
            mappedZenhubAhaReleases[zenhubReleasesMap[ahaReleaseName]] = ahaReleaseId
            #Update the Aha Theme so that next time there is no need for a names check. 
            logger.warning("Mapped the release by name in Aha {0} :".format(ahaReleaseName))
            Aha.updateAhaReleaseTheme(ahaReleaseId, zenhubReleasesMap[ahaReleaseName])
        else:
            Aha.unmappedAhaReleases += ahaReleaseName

    Aha.mappedAhaZenhubReleases = mappedAhaZenhubReleases
    Aha.mappedZenhubAhaReleases = mappedZenhubAhaReleases
    
def CreateOrUpdateReleaseData(Aha, Zenhub):
    for ahaReleaseId, ahaRelease in Aha.openReleasesMap.items():
        try:
            zenhubReleaseId = Aha.mappedAhaZenhubReleases[ahaReleaseId]
        except KeyError:
            zenhubReleaseId = None
        
        if  zenhubReleaseId is not None:
            #Mapping found. Just update the data.
            Aha.updateAhaRelease(ahaReleaseId, Zenhub.releases[zenhubReleaseId])
            logger.info("Updated the following Release successfully: {0}".format(ahaRelease["name"]))
        else: 
            #Mapping not found. Create a release in Zenhub
            zenhubRelease = Zenhub.createNewRelease(ahaRelease)
            zenhubReleaseId = zenhubRelease["release_id"]
            Aha.updateAhaReleaseTheme(ahaReleaseId, zenhubReleaseId)
            logger.info("Successfully created a new Release in Zenhub for Aha release {0}".format(ahaRelease["name"]))

def CreateOrUpdateEpicsData(Aha, Zenhub):
    for ahaReleaseId, ahaRelease in Aha.openReleasesMap.items():

        #For Each OpenRelease sync all the epic data. 

        epicsMap = Aha.getEpicsMapForRelease(ahaReleaseId)
        logger.info("Syncing {0} epics for the release : {1}".format(len(epicsMap), ahaRelease["name"]))

        for ahaEpicId, ahaEpicData in epicsMap.items():

            try:
                zenhubEpicId = Aha.mappedAhaZenhubEpics[ahaEpicId]
            except KeyError:
                zenhubEpicId = None

            ahaReleaseId = ahaEpicData["release"]["id"]
            zenhubReleaseId = Aha.mappedAhaZenhubReleases[ahaReleaseId]
            
            if zenhubEpicId is not None:
                #Mapping found. Sync the details of the epic back from zenhub
                zenhubData = Zenhub.getEpicData(zenhubEpicId)
                Aha.updateAhaEpic(ahaEpicId, zenhubData , ahaEpicData)
                Zenhub.updateZenhubEpicAndRelease(zenhubEpicId, zenhubReleaseId)
                logger.info("Successfully updated epic in aha from zenhub {0}".format(ahaEpicData["name"]))
            else:
                epicBody = ahaEpicData["description"]["body"]
                zenhubEpic = Zenhub.createZenhubEpic(ahaEpicData["name"], epicBody, zenhubReleaseId)
                Aha.updateAhaEpicLink(ahaEpicId, epicBody, zenhubEpic.number)
                logger.info("Successfully created a new epic in zenhub for Aha Release {0}".format(ahaEpicData["name"]))
                #logger.warn("Need to create a new Zenhub Epic for the following Aha epic: {0}".format(ahaEpicData["name"]))

if __name__ == "__main__":
    main()