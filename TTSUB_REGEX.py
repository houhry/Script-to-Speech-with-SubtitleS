import re


class TtsubRegex:

    def sub(self, to_sub, sub_with, text):
        return re.sub(to_sub, sub_with, text)

    def search(self, to_search, text):
        print(to_search)
        print(text)
        x = re.search(to_search, text)
        if x is not None:
            return x.start()
        return None

    def match(self, to_search, text):
        x = None
        for x in re.finditer(to_search, text):
            pass
        if x is not None:
            return x.group()
        return None

    def get_value(self, name, value_format, text):
        x = None
        for x in re.finditer("(?<=" + name + value_format + ")" + r"\d+(?="+value_format + ")", text):
            pass
        # search for the first number element after KEY
        if x is not None:
            return int(x.group())  # return the value not string
        return None

    def clear_cmd_and_value(self, name, value_format, text):
        return re.sub(name + value_format + ".*?" + value_format, "", text)

    def clear_cmd(self, name, text):
        return re.sub(name, "", text)

    def get_string(self, name, value_format, text):
        x = None
        print("(?<=" + name + value_format + ")" + ".*?(?=" + value_format + ")")
        for x in re.finditer("(?<=" + name + value_format + ")" + ".*?(?=" + value_format + ")", text):
            pass
        # search for the first element after KEY
        if x is not None:
            print(x)
            return x.group()  # return the string
        return None
