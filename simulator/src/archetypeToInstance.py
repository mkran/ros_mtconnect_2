import os,sys
sys.path.insert(0,os.getcwd()+'\\taskArchetype') #child path
sys.path.insert(0, os.path.dirname(os.getcwd())) #parent
import xml.etree.ElementTree as ET
import uuid, re
import datetime, copy

class archetypeToInstance(object):

    def __init__(self, task, uuid, deviceUuid, parentRef = "None"):

        self.parentRef = parentRef
        self.taskArch = task
        self.jsonModel = {}
        self.taskCoordinator = None
        self.root = self.readArchetype(self.taskArch)
        self.uuid = uuid
        self.deviceUuid = deviceUuid
        self.taskIns = ET.tostring(self.toInstance(deviceUuid = self.deviceUuid))
        

    def readArchetype(self, taskArch):
        try:
            fileOpen = open(os.path.join('taskArchetype', taskArch +'.xml'))
            fileRead = fileOpen.read()
            root = ET.fromstring(fileRead)
        except:
            #for mamba
            fileOpen = open('../src/taskArchetype/'+taskArch+'.xml')
            fileRead = fileOpen.read()
            root = ET.fromstring(fileRead)


        return root

    def formatTaskArch(self, taskArch):
        taskFormat = taskArch.split('_')[0]
        taskFormat = re.findall('[A-Z][^A-Z]*', taskFormat)
        
        return '_'.join(taskFormat).upper()

    def formatTaskType(self, taskType):
        taskType = taskType.lower().split('_')
        for i,x in enumerate(taskType):
            taskType[i] = x.capitalize()
        return ''.join(taskType)

    def toInstance(self, deviceUuid = "None"):
        if type(self.root) == ET.Element:
            
            taskIns = ET.Element("Task")
            taskIns.attrib["assetId"] = str(self.uuid)
            taskIns.attrib["timestamp"] = str(datetime.datetime.now().isoformat()+'Z')
            taskIns.attrib["deviceUuid"] = str(self.deviceUuid)

            assetArchRef = ET.SubElement(taskIns, "AssetArchetypeRef")
            assetArchRef.attrib["assetId"] = str(self.taskArch)

            priority = ET.SubElement(taskIns, "Priority")
            priority.text = str(1) #to be updated later

            """
            if self.parentRef!="None":
                parentRef = ET.SubElement(taskIns, "ParentRef")
                parentRef.text = self.parentRef
            """
            taskType = ET.SubElement(taskIns, "TaskType")
            taskType.text = self.formatTaskArch(self.taskArch).upper()

            state = ET.SubElement(taskIns, "State")
            state.text = str("INACTIVE")

            coordinator = ET.SubElement(taskIns, "Coordinator")
            coordinator.attrib["collaboratorId"] = self.root.findall('.//'+self.root.tag.split('}')[0]+'}Coordinator')[0].attrib['collaboratorId']
            self.taskCoordinator = coordinator.attrib["collaboratorId"]
            #print coordinator.attrib["collaboratorId"]
            coordinator.text = self.root.findall('.//'+self.root.tag.split('}')[0]+'}Coordinator')[0][0].text

            for i,x in enumerate(self.root.findall('.//'+self.root.tag.split('}')[0]+'}Collaborators')[0]):
                collaborator = ET.SubElement(taskIns, "Collaborator")
                collaborator.attrib["collaboratorId"] = str(x.attrib['collaboratorId']) #update this later
                collaborator.text = str(x[0].text)
            

            self.taskIns = taskIns
            return taskIns
        else:
            return None

    def addElement(self, string):
        if type(self.taskIns) == ET.Element:
            self.taskIns.append(ET.fromstring(string))
        elif type(self.taskIns) == str:
            newTaskins = ET.fromstring(copy.deepcopy(self.taskIns))
            newTaskins.append(ET.fromstring(string))
            return ET.tostring(newTaskins)


    def traverse(self, root, jsonSubTaskModel = {}):
        if root.findall('.//'+root.tag.split('}')[0]+'}SubTaskRef'):
            jsonSubTaskModel[root.findall('.//'+root.tag.split('}')[0]+'}TaskArchetype')[0].attrib['assetId']] = {}
            
            for x in root.findall('.//'+root.tag.split('}')[0]+'}SubTaskRef'):

                childRoot = self.readArchetype(x.text)
                collaborators = []
                for y in childRoot.findall('.//'+childRoot.tag.split('}')[0]+'}Collaborator'):
                    collaborators.append(y.attrib['collaboratorId'])
                taskType = self.formatTaskType(childRoot.findall('.//'+root.tag.split('}')[0]+'}TaskType')[0].text)

                jsonSubTaskModel[root.findall('.//'+root.tag.split('}')[0]+'}TaskArchetype')[0].attrib['assetId']][childRoot.findall('.//'+root.tag.split('}')[0]+'}TaskArchetype')[0].attrib['assetId']] = {'order':x.attrib['order'], 'coordinator':childRoot.findall('.//'+root.tag.split('}')[0]+'}Coordinator')[0].attrib['collaboratorId'], 'collaborators':collaborators, 'TaskType':taskType}
         
                self.traverse(childRoot,jsonSubTaskModel[root.findall('.//'+root.tag.split('}')[0]+'}TaskArchetype')[0].attrib['assetId']][childRoot.findall('.//'+root.tag.split('}')[0]+'}TaskArchetype')[0].attrib['assetId']])

            return jsonSubTaskModel
            
        else:
            return jsonSubTaskModel

        
    #very much work in progress 
    def jsonInstance(self):
        jsonModel = {}
        jsonModel['coordinator']={}
        jsonModel['collaborators']={}
        subTaskModel = self.traverse(self.root,{})
        CoordinatorSubTask = {}
        CollaboratorSubTask = {}
        
        for x in self.root.findall('.//'+self.root.tag.split('}')[0]+'}TaskArchetype')[0]:
            if 'coordinator' in x.tag.lower():
                coordinator = x.attrib['collaboratorId']
                coordinatorType = x[0].text.lower()
                CoordinatorSubTask[x.attrib['collaboratorId']] = []
            elif 'priority' in x.tag.lower():
                priority = x.text
            elif 'tasktype' in x.tag.lower():
                tasktype = x.text.lower()
            elif 'collaborators' in x.tag.lower():
                for y in x:
                    jsonModel['collaborators'][y.attrib['collaboratorId']]={'state':[y[0].text,y.attrib['collaboratorId'],None],'SubTask':{}}
                                                
                    CoordinatorSubTask[y.attrib['collaboratorId']] = []

        i=0
        for key, val in subTaskModel.values()[0].iteritems():
            i+=1
            if len(val['collaborators']) == 1:
                collaborators = val['collaborators'][0]

            taskType = val['TaskType']
                
            CoordinatorSubTask[val['coordinator']] = [key, None, collaborators,taskType, i]
            if key in val:
                for keys, vals in val[key].iteritems():
                    if not jsonModel['collaborators'][vals['coordinator']]['SubTask']:
                        jsonModel['collaborators'][vals['coordinator']]['SubTask'][key] = []
                    jsonModel['collaborators'][vals['coordinator']]['SubTask'][key].append(['Interface',keys, None, vals['order'], None])

                if vals:
                    jsonModel['collaborators'][vals['coordinator']]['SubTask'][key] = sorted(jsonModel['collaborators'][vals['coordinator']]['SubTask'][key], key=lambda x: x[3])
                    

        jsonModel['coordinator']={coordinator:{'state':[coordinatorType,coordinator,None],'Task':[tasktype,None], 'SubTask':CoordinatorSubTask}}


        self.jsonModel = jsonModel

        return jsonModel


def update(taskIns, dataitem, value):
    if type(taskIns) == ET.Element:
        if taskIns.findall('.//'+dataitem)[0].text != value:
            taskIns.attrib['timestamp'] = datetime.datetime.now().isoformat() + 'Z'
            taskIns.findall('.//'+dataitem)[0].text = value
        return taskIns
    else:
        taskIns = ET.fromstring(taskIns)
        if taskIns.findall('.//'+dataitem)[0].text != value:
            taskIns.attrib['timestamp'] = datetime.datetime.now().isoformat() + 'Z'
            taskIns.findall('.//'+dataitem)[0].text = value
        return ET.tostring(taskIns)
            
            
        
    
            

if __name__ == "__main__":
    #print archetypeToInstance("MoveMaterial_2","xyz","cnc1").jsonInstance()
    print datetime.datetime.now().isoformat()
    a2i = archetypeToInstance("MoveMaterial_2","xyz","cnc1")
    a2i.jsonInstance()
    print datetime.datetime.now().isoformat()
    
    

        

        
