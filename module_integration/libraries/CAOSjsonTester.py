__INT_KEYWORDS__ = ["@Integer@", "@Float@", "@int@", "@float@"]
__STR_KEYWORDS__ = ["@string@", "@str@", "@String@"]
__BOOL_KEYWORDS__ = ["@Bool@", "@bool@", "@Boolean@"]
__LIST_KEYWORDS__ = ["@list@"]
__DICT_KEYWORDS__ = ["@dict@"]
__ITEM_KEYWORD__ = "@item@"
__ANY_KEYWORD__ = "@any@"


class InvalidItem(Exception):
    pass


def _validate_item(item, validator_item):
    if type(validator_item) is str or type(validator_item) is unicode:
        if __ANY_KEYWORD__ in validator_item:
            return
        if ((validator_item in __LIST_KEYWORDS__ and type(item) is not list) or
            (validator_item in __STR_KEYWORDS__ and type(item) is not str and type(item) is not unicode) or
            (validator_item in __INT_KEYWORDS__ and
             type(item) not in (int, float)) or
            (validator_item in __BOOL_KEYWORDS__ and type(item) is not bool) or
            (validator_item in __DICT_KEYWORDS__ and type(item) is not dict) or
            (validator_item not in (__INT_KEYWORDS__ + __INT_KEYWORDS__ +
                                    __STR_KEYWORDS__ + __BOOL_KEYWORDS__ +
                                    __LIST_KEYWORDS__ + __DICT_KEYWORDS__) and
                validator_item != item)):
            raise InvalidItem()
    elif type(validator_item) in (bool, int, float):
        if item != validator_item:
            raise InvalidItem()
    elif type(validator_item) in (dict, list):
        _validate_json_helper(item, validator_item)
    else:
        raise InvalidItem()


def _validate_list(item, validator_list):
    if ((not [i for i in __LIST_KEYWORDS__ if i in validator_list] and
         type(item) is list) or
        (not [i for i in __STR_KEYWORDS__ if i in validator_list] and
         type(item) is str) or
        (not [i for i in __STR_KEYWORDS__ if i in validator_list] and
         type(item) is unicode) or
        (not [i for i in __INT_KEYWORDS__ if i in validator_list] and
         type(item) in (int, float)) or
        (not [i for i in __DICT_KEYWORDS__ if i in validator_list] and
            type(item) is dict)):
        if type(item) in (float, int, str, unicode, bool):
            if item not in validator_list:
                raise InvalidItem()
        elif type(item) in (dict, list):
            for v in validator_list:
                try:
                    _validate_json_helper(item, v)
                    break
                except InvalidItem:
                    pass
            else:
                raise InvalidItem()
        else:
            raise InvalidItem()


def _validate_json_helper(jsonPayload, validator):
    if type(validator) is list and type(jsonPayload) is list:
        for item in jsonPayload:
            _validate_list(item, validator)
    elif type(validator) is dict and type(jsonPayload) is dict:
        for key, item in jsonPayload.items():
            if key in validator:
                _validate_item(item, validator[key])
            else:
                variants = [v for k, v in validator.items()
                            if __ITEM_KEYWORD__ in k]
                for v in variants:
                    try:
                        _validate_item(item, v)
                        break
                    except InvalidItem:
                        pass
                else:
                    raise InvalidItem()
    else:
        raise InvalidItem()


def validate_json(jsonPayload, validator):
    try:
        _validate_json_helper(jsonPayload, validator)
        return True
    except InvalidItem:
        return False
    return False
