from ._mapi import MidasAPI , NX
# from ._model import *

from typing import Literal, Optional, cast

# from ._model import *

_classification = Literal["General", "Steel", "Concrete", "SRC", "Composite Steel Girder", "Seismic", "All"]
_active = Literal["STRENGTH" , "SERVICE" , "INACTIVE" , "ACTIVE"]
_type = Literal["Add","Envelope","ABS","SRSS"]

#28 Class to generate load combinations
class LoadCombination:
    data = []
    valid = ["General", "Steel", "Concrete", "SRC", "Composite Steel Girder", "Seismic", "All"]
    com_map = {
            "General": "/db/LCOM-GEN",
            "Steel": "/db/LCOM-STEEL",
            "Concrete": "/db/LCOM-CONC",
            "SRC": "/db/LCOM-SRC",
            "Composite Steel Girder": "/db/LCOM-STLCOMP",
            "Seismic": "/db/LCOM-SEISMIC"
        }

    @staticmethod
    def _existing_ids(classification):
        """Return existing MIDAS IDs for a load-combination classification."""
        endpoint = LoadCombination.com_map.get(classification)
        if endpoint is None:
            return set()

        try:
            res = MidasAPI("GET", endpoint)
        except Exception:
            return set()

        if not isinstance(res, dict):
            return set()

        root_key = endpoint.split("/")[-1].split("-")[-1]
        body = res.get(root_key, {})
        if not isinstance(body, dict):
            return set()

        ids = set()
        for k in body.keys():
            try:
                ids.add(int(k))
            except (TypeError, ValueError):
                continue
        return ids

    @staticmethod
    def _ids_to_suffix(ids):
        if not ids:
            return ""
        return "/" + ",".join(str(i) for i in sorted(ids))
    def __init__(self, name, case, classification:_classification = "General", active:_active = "ACTIVE", typ:_type = "Add", id: Optional[int] = None, desc = ""):
        """Name, List of tuple of load cases & factors, classification, active, type. \n
        Sample: LoadCombination('LCB1', [('Dead Load(CS)',1.5), ('Temperature(ST)',0.9)], 'General', 'Active', 'Add')"""
        if id == None: id =0
        if not isinstance(case, list):
            print("case should be a list that contains tuple of load cases & factors.\nEg: [('Load1(ST)', 1.5), ('Load2(ST)',0.9)]")
            return
        for i in case:
            if not isinstance(i, tuple):
                print(f"{i} is not a tuple.  case should be a list that contains tuple of load cases & factors.\nEg: [('Load1(ST)', 1.5), ('Load2(ST)',0.9)]")
                return
            if not isinstance(i[0], str):
                print(f"{i[0]} is not a string.  case should be a list that contains tuple of load cases & factors.\nEg: [('Load1(ST)', 1.5), ('Load2(ST)',0.9)]")
                return
            if i[0][-1] != ")":
                print(f"Load case type is not mentioned for {i[0]}.  case should be a list that contains tuple of load cases & factors.\nEg: [('Load1(ST)', 1.5), ('Load2(ST)',0.9)]")
                return
            if not isinstance(i[1],(int, float)):
                print(f"{i[1]} is not a number.  case should be a list that contains tuple of load cases & factors.\nEg: [('Load1(ST)', 1.5), ('Load2(ST)',0.9)]")
                return

        if classification not in LoadCombination.valid[:-1]:
            print(f'"{classification}" is not a valid input.  It is changed to "General".')
            classification = "General"
            
        if classification in ["General", "Seismic"]:
            if active not in ["ACTIVE", "INACTIVE"]: active = "ACTIVE"
        if classification in  ["Steel", "Concrete", "SRC", "Composite Steel Girder"]:
            if active not in ["STRENGTH", "SERVICE", "INACTIVE"]: active = "STRENGTH"
        
        typ_map = {"Add": 0, "Envelope": 1, "ABS": 2, "SRSS": 3, 0:0, 1:1, 2:2, 3:3}
        if typ not in list(typ_map.keys()): typ = "Add"
        if classification not in ["General", "Seismic"] and typ_map.get(typ) == 2: typ = "Add"
        
        if id == 0 and len(LoadCombination.data) == 0: 
            id = 1
        elif id == 0 and len(LoadCombination.data) != 0:
            id = max([i.ID for i in LoadCombination.data]) + 1
        elif id != 0 and id in [i.ID for i in LoadCombination.data]:
            if classification in [i.CLS for i in LoadCombination.data if i.ID == id]:
                print(f"ID {id} is already defined.  Existing combination would be replaced.")
                
        
        combo = []
        valid_anl = ["ST", "CS", "MV", "SM", "RS", "TH", "CB", "CBC", "CBS", "CBR", "CBSC", "CBSM"] #Need to figure out for all combination types
        for i in case:
            a = i[0].rsplit('(', 1)[1].rstrip(')')
            if a in valid_anl:
                combo.append({
                    "ANAL": a,
                    "LCNAME":i[0].rsplit('(', 1)[0],
                    "FACTOR": i[1]
                })
        self.NAME = name
        self.CASE = combo
        self.CLS = classification
        self.ACT = active
        self.TYPE = typ_map.get(typ)
        self.ID = id
        self.DESC = desc
        LoadCombination.data.append(self)
    
    @classmethod
    def json(cls, classification = "All"):
        if len(LoadCombination.data) == 0:
            print("No Load Combinations defined!  Define the load combination using the 'LoadCombination' class before making json file.")
            return
        if classification not in LoadCombination.valid:
            print(f'"{classification}" is not a valid input.  It is changed to "General".')
            classification = "General"
        json = {k:{'Assign':{}} for k in LoadCombination.valid[:-1]}
        for i in LoadCombination.data:
            if i.CLS == classification or classification == "All":
                json[i.CLS]['Assign'][i.ID] = {
                    "NAME": i.NAME,
                    "ACTIVE": i.ACT,
                    "iTYPE": i.TYPE,
                    "DESC": i.DESC,
                    "vCOMB":i.CASE
                }
        json = {k:v for k,v in json.items() if v != {'Assign':{}}}
        return json
    
    @classmethod
    def get(cls, classification = "All"):
        if classification not in LoadCombination.valid:
            print(f'"{classification}" is not a valid input.  It is changed to "General".')
            classification = "General"
        combos = {k:{} for k in LoadCombination.valid[:-1]}
        for i in LoadCombination.valid[:-1]:
            if classification == i or classification == "All":
                endpoint = LoadCombination.com_map.get(i)
                if endpoint is None:
                    continue
                combos[i] = MidasAPI("GET", endpoint)
        json = {k:v for k,v in combos.items() if v != {'message':''}}
        return json
    
    @classmethod
    def create(cls, classification = "All"):
        if len(LoadCombination.data) == 0:
            # print("No Load Combinations defined!  Define the load combination using the 'LoadCombination' class before creating these in the model.")
            return
        if classification not in LoadCombination.valid:
            print(f'"{classification}" is not a valid input.  It is changed to "General".')
            classification = "General"
        json = LoadCombination.json(classification)
        if not json:
            return
        for i in LoadCombination.valid[:-1]:
            if classification == i or classification == "All":
                if i in list(json.keys()):
                    endpoint = LoadCombination.com_map.get(i)
                    if endpoint is None:
                        continue

                    requested_ids = set()
                    for k in json[i]['Assign'].keys():
                        try:
                            requested_ids.add(int(k))
                        except (TypeError, ValueError):
                            continue

                    existing_ids = LoadCombination._existing_ids(i)
                    delete_ids = requested_ids.intersection(existing_ids)
                    delete_suffix = LoadCombination._ids_to_suffix(delete_ids)
                    if delete_suffix:
                        _current_dispWarning = NX.dispWarning
                        NX.dispWarning = False
                        MidasAPI("DELETE", endpoint + delete_suffix)
                        NX.dispWarning = _current_dispWarning
                    MidasAPI("PUT", endpoint, json[i])   #Create new combination
    
    @classmethod
    def sync(cls, classification = "All"):
        LoadCombination.clear()
        json = LoadCombination.get(classification)
        if json:
            keys = list(json.keys())
            for i in keys:
                endpoint = LoadCombination.com_map.get(i)
                if endpoint is None:
                    continue
                root_key = endpoint[4:]
                section = json[i].get(root_key, {})
                for k,v in section.items():
                    c = []
                    for j in range(len(v['vCOMB'])):
                        c.append((v['vCOMB'][j]['LCNAME'] + "("+ v['vCOMB'][j]['ANAL'] + ")", v['vCOMB'][j]['FACTOR']))
                    LoadCombination(v['NAME'], c, cast(_classification, i), v['ACTIVE'], v['iTYPE'], int(k), v['DESC'])
    
    @classmethod
    def delete(cls, classification = "All", ids = []):
        json = LoadCombination.json(classification)
        if not json:
            print("No load combinations are defined to delete.")
            return

        requested_ids = set()
        for i in ids:
            try:
                requested_ids.add(int(i))
            except (TypeError, ValueError):
                continue

        if not requested_ids:
            return

        for i in list(json.keys()):
            endpoint = LoadCombination.com_map.get(i)
            if endpoint is None:
                continue
            existing_ids = LoadCombination._existing_ids(i)
            delete_ids = requested_ids.intersection(existing_ids)
            delete_suffix = LoadCombination._ids_to_suffix(delete_ids)
            if delete_suffix:
                MidasAPI("DELETE", endpoint + delete_suffix)

    @classmethod
    def clear(cls):
        cls.data = []
#---------------------------------------------------------------------------------------------------------------