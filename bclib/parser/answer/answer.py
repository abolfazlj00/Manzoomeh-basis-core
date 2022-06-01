import json
from typing import Any, Callable
from bclib import edge, db_manager
from .user_action_types import UserActionTypes
from .user_action import UserAction


class Answer:
    """BasisJsonParser is a tool to parse basis_core components json objects. This tool is developed based on
             basis_core key and values."""

    def __init__(self, data: 'str|Any', api_url: 'str' = None):
        self.json = json.loads(data) if isinstance(data, str) else data
        self.__answer_list: 'list[UserAction]' = None
        self.__api_connection = db_manager.RESTfulConnection(
            api_url) if api_url else None

    async def __fill_answer_list_async(self):
        self.__answer_list = list()
        for data in self.json['properties']:
            for action_type in UserActionTypes:
                if action_type.value in list(data.keys()):
                    for actions in data[action_type.value]:
                        if 'parts' in actions.keys():
                            for parts in actions['parts']:
                                for values in parts['values']:
                                    prp_id = data['propId']
                                    prp_value_id = actions['id'] if 'id' in actions.keys(
                                    ) else None
                                    part_number = parts['part'] if "part" in parts.keys(
                                    ) else None
                                    value_id = values['id'] if "id" in values.keys(
                                    ) else None
                                    value = values['value']
                                    self.__answer_list.append(UserAction(
                                        prp_id, action_type, prp_value_id, value_id, value, None, None, part_number))
                        else:
                            prp_id = data['propId']
                            prp_value_id = actions['id'] if 'id' in actions.keys(
                            ) else None
                            self.__answer_list.append(UserAction(
                                prp_id, action_type,  prp_value_id, None, None, None, None, None))

        await self.__try_set_data_type_async()

    async def __get_action_async(self, prp_id_list: 'list[int]', action_list: 'list[UserActionTypes]', part_list: 'list[int]', predicate: 'Callable[[UserAction],bool]' = None) -> 'list[UserAction]':
        ret_val: 'list[UserAction]' = None
        if self.__answer_list is None:
            await self.__fill_answer_list_async()

        if predicate:
            ret_val = [x for x in self.__answer_list if predicate(x)]
        else:
            ret_val = [x for x in self.__answer_list if
                       (prp_id_list is None or x.prp_id in prp_id_list) and
                       (action_list is None or x.action in action_list) and
                       (part_list is None or x.part in part_list)
                       ]
        return ret_val if ret_val else list()

    async def get_actions_async(self, prp_id: 'int|list[int]' = None, action: 'UserActionTypes|list[UserActionTypes]' = None,
                                part: int = None, predicate: 'Callable[[UserAction],bool]' = None) -> 'list[UserAction]':
        """
        inputs:
        prpid: None, int or list
        action: None, int or list
        part: None or in
        Samples:
        (prpid=None, action='edited')
        (prpid=[12345, 1000], action=None)
        """

        action_list = [action] if isinstance(
            action, UserActionTypes) else action
        prp_id_list = [prp_id] if isinstance(prp_id, int) else prp_id
        part_list = [part] if isinstance(part, int) else part
        return await self.__get_action_async(prp_id_list, action_list, part_list, predicate)

    def __data_type_checker(self, view_type: str, datatype: str = None):

        if view_type in ["select", "checkList"]:
            result = "fixvalue"
        elif view_type == "textarea":
            result = "ntextvalue"
        elif view_type == "text" and datatype in ["text", "None", None]:
            result = "textvalue"
        elif view_type == "text" and datatype == "int":
            result = "numvalue"
        elif view_type == "text" and datatype == "float":
            result = "floatvalue"
        elif view_type == "autocomplete":
            result = "autocomplete"
        else:
            result = "None"
        return result

    async def __try_set_data_type_async(self):
        if self.__api_connection:
            type_list = list()
            questions_data = edge.DictEx(await self.__api_connection.post_async())
            for data in questions_data.sources:
                for question in data.data:
                    for parts in question.questions:
                        for validations in parts.parts:
                            data_type = validations.validations["datatype"] if "datatype" in validations.validations.keys(
                            ) else "None"
                            type_list.append({
                                "prpId": parts.prpId, "part": validations.part, "viewtype": validations.viewType,
                                "datatype": data_type, "table": self.__data_type_checker(validations.viewType, data_type)
                            })
            for type in type_list:
                for values in self.__answer_list:
                    if int(type['prpId']) == int(values.prp_id) and type["part"] == values.part or values.part is None:
                        values.datatype = type['table']