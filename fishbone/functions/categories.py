import logging

class Formatter(object):
    """Plugins of this class convert plain text to HTML"""
    name = "No Format"
    def formatText(self, text):
        """Takes plain text, returns HTML"""
        return text

class Database_category(object):
    """Plugins of this class operate on a database"""
    name = "Null format"
    def formatText(self, text):
        """Takes plain text, returns HTML"""
        return text
    
    def tablemodify(self,type,DATABASE,start,end):
        """Takes plain text, returns HTML"""
        name=""
        return name
    
class Data_row_modify(object):
    name="Null category main: data_row_modify"
    def __init__(self):
        logging.info("INIT: "+str(self.name))
        
    def tablemodify(self,**kwargs):
    #def tablemodify(self,type,DATABASE,start,end):
        """Takes plain text, returns HTML ... though now returns dictionary"""
        name=""
        return name
    
    def debug(self, **kwargs):
        """Returns text showing what ran"""
        text="jdebug"
        return text
    
    
class API_launcher(object):
    name="Launches APIs category main"
    
    def __init__(self):
        logging.info("INIT: "+str(self.name))
        
    def main_runapi(self,**kwargs):
        """Takes plain text, returns HTML"""
        name=""
        return name
    
    def debug(self, **kwargs):
        text="jdebug"
        return text

    
    
    