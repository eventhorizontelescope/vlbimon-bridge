str_to_type = {  # these are the only valid types
    'int': int,
    'float': float,
    'str': str,
    'bool': bool,
}


def get_types():
    ret = {}
    with open('vlbimon_types.csv') as fd:
        for line in fd:
            #print(line)
            line = line.strip()
            name, type = line.split(',')  # yeah, crash if too many ,
            ret[name] = str_to_type[type]
    return ret
