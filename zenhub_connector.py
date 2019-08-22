from urllib.parse import urljoin
from github import Github
import requests
import logging


logger = logging.getLogger("root")

class ZenhubConnector:
    def __init__(self, config):
        self.config = config
        self.ZENHUB_HEADER={'X-Authentication-Token':config.ZENHUB_TOKEN}
        self.releaseNamesMap = {}

        self.releases = self.__getZenhubReleases()
        self.github = self.__initializeGit() 
        
        

    
    def __getZenhubReleases(self):
        url=urljoin(self.config.Zenhub_Domain,'/p1/repositories/{0}/reports/releases'.format(str(self.config.Zenhub_repo_Id)))
        rs= requests.get(url=url, headers=self.ZENHUB_HEADER)
        if(rs.status_code==200):
            releases = rs.json()
            releaseMap = {}
            for release in releases:
                releaseMap[release['release_id']] = release
                self.releaseNamesMap[release['title']] = release['release_id']
            
            return releaseMap

        else:
            logger.error("Error in getting Zenhub releases : {0}".format(rs.json()))


    def createNewRelease(self, ahaRelease):
        url=urljoin(self.config.Zenhub_Domain, '/p1/repositories/{repo_id}/reports/release'.format(repo_id = self.config.Zenhub_repo_Id))
        
        data = {
            "title": ahaRelease["name"],
            "start_date": ahaRelease["start_date"] +"T00:00:00Z",
            "desired_end_date": ahaRelease["start_date"] + "T00:00:00Z"
        }
        rs = requests.post(url = url, json=data, headers=self.ZENHUB_HEADER)
        if (rs.status_code == 200):
            return rs.json()
        else:
            logger.error("Error in creating the release in Zenhub for ahaRelease {0}".format(data["title"]))


    def getEpicData(self, issueId):
        url= urljoin(self.config.Zenhub_Domain,'/p1/repositories/{0}/issues/{1}'.format(str(self.config.Zenhub_repo_Id),str(issueId)))
        rs= requests.get(url=url, headers=self.ZENHUB_HEADER)
        if(rs.status_code==200):
            result= rs.json()
            result['id']=issueId
            #logger.info("Found following epic data for epic {0} : {1}".format(issueId, result))
            return result
        else:
            #Log error
            logger.error("Error getting zenhub issue or id:{0}".format(issueId))
            return None


    def __initializeGit(self):
        return Github(self.config.GITHUB_TOKEN).get_repo(self.config.repo_name)

    def createZenhubEpic(self, title, details, zenhubReleaseId):
        issue = self.github.create_issue(title=title, body=details, labels=["Epic"])

        logger.warn("Issue created via github : {0}".format(issue))

        self.__convertIssueToEpic(issue.number)
        self.__moveToDefaultPipeline(issue.number)

        self.updateZenhubEpicAndRelease(issue.number, zenhubReleaseId)
        return issue

    def __convertIssueToEpic(self, issueNumber):
        url = urljoin(self.config.Zenhub_Domain, '/p1/repositories/{repo_id}/issues/{issue_number}/convert_to_epic'.format(repo_id = self.config.Zenhub_repo_Id, issue_number = issueNumber))

        data = {
            "issues" : []
        }

        rs = requests.post(url = url, json=data, headers=self.ZENHUB_HEADER)
        if (rs.status_code==200):
            logger.info("Successfully convered Issue to Epic for : {0}".format(issueNumber))
        else:
            logger.error("Error in converting Issue to Epic for {0}".format(issueNumber))
    

    def updateZenhubEpicAndRelease(self, zenhubIssueNumber, zenhubReleaseId):
        url= urljoin(self.config.Zenhub_Domain,'/p1/reports/release/{0}/issues'.format(zenhubReleaseId))
        data = {
            "add_issues":[{"repo_id": int(self.config.Zenhub_repo_Id), "issue_number":int(zenhubIssueNumber)}],
            "remove_issues":[]
        }
        rs= requests.patch(url=url, json=data, headers=self.ZENHUB_HEADER)
        if(rs.status_code==200):
            logger.info("Successfully linked release {0} and epic {1}".format(zenhubReleaseId, zenhubIssueNumber))
        else:
            #Log error
            logger.error("Error Linking epic :{0} and release: {1} with error {2}".format(zenhubIssueNumber, zenhubReleaseId, rs))
            return None

    def __moveToDefaultPipeline(self, issueNumber):
        url = urljoin(self.config.Zenhub_Domain, 
        '/p2/workspaces/{workspace_id}/repositories/:repo_id/issues/{issue_number}/moves'. format(workspace_id = self.config.workspace_id, issue_number = issueNumber))

        data = {
            "pipeline_id" : self.config.default_pipeline_id,
            "position" : "bottom"
        }
        rs = requests.post(url = url, json = data, headers = self.ZENHUB_HEADER)

        if rs.status_code == 200:
            logger.info("Successfully moved the issue to Functional Analysis: {0}".format(issueNumber))
        else:
            logger.error("Error moving application to default pipeline")



