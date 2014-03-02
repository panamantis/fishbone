from django.db import models
from djangotoolbox import fields

import datetime
import logging

from django.utils.translation import ugettext_lazy as _

class dashydb(models.Model):
    def __init(self):
        self.myself=self
        
    now=datetime.datetime.now()
    concept_id=models.CharField(max_length=40,default="",null=True,blank=True)
    myparent   =models.CharField(max_length=30,default="",null=True,blank=True)
    mychildren =fields.ListField(models.CharField(max_length=15),null=True,blank=True)
    mytools    =fields.ListField(models.CharField(max_length=15),null=True,blank=True)
    type      =models.CharField(max_length=20,default="",null=True,blank=True)
    category1=models.CharField(max_length=20,default="",null=True,blank=True)
    category2=models.CharField(max_length=20,default="",null=True,blank=True)
    tags =fields.ListField(models.CharField(max_length=15),null=True,blank=True)
    
    description=models.CharField(max_length=300,default="",null=True,blank=True)
    mylist    =fields.ListField(models.CharField(max_length=20),null=True,blank=True)
    myfield=models.CharField(max_length=280,default="",null=True,blank=True)
    mytext = models.TextField(blank=True)

    tagtree=fields.ListField(fields.EmbeddedModelField('TagTreeDB'),default=[])
    url        =models.CharField(max_length=200,default="",null=True,blank=True)
    url_media   =models.CharField(max_length=200,default="",null=True,blank=True)
    state=models.CharField(max_length=20,default="",null=True,blank=True)
    
    timestamp=models.DateTimeField(default=now)
    
    def to_dict(self):
        return dict([(p, unicode(getattr(self, p))) for p in self.properties()])
    
    def __unicode__(self):
        self.title=self.concept_id
        return self.title
   
    def __str__(self):
        return self.title

    class Admin:
        pass
    
    def save(self, *args, **kwargs):
        ok_to_save=True
        
        # LISTFIELD bug catcher if try to save as string
        if self.mytools:
            if (isinstance(self.mytools,list)): #ok
                pass
            elif self.mytools=='None':
                self.mytools=[]
            else:
                # Try to convert to array if looks like one (ie/ from form submit!)
                try: 
                    temp = eval(self.mytools)
                    logging.debug("Converted string to list")
                    self.mytools=temp
                except:
                    logging.error("mytools SAVE ERROR at ["+str(self.id)+"]: NOT ALLOWING to save string as list given: "+str(self.mytools))
                    ok_to_save=False
        # LISTFIELD bug catcher if try to save as string
        if self.tags:
            if (isinstance(self.tags,list)): #ok
                pass
            elif self.tags=='None':
                self.tags=[]
            else:
                try: # Try to convert to array if looks like one (ie/ from form submit!)
                    temp = eval(self.tags)
                    logging.debug("Converted string to list")
                    self.tags=temp
                except:
                    logging.error("tags SAVE ERROR at ["+str(self.id)+"]: NOT ALLOWING to save string as list given: "+str(self.tags))
                    ok_to_save=False
        # LISTFIELD bug catcher if try to save as string
        if self.mylist:
            if (isinstance(self.mylist,list)): #ok
                pass
            elif self.mylist=='None':
                self.mylist=[]
            else:
                try: # Try to convert to array if looks like one (ie/ from form submit!)
                    temp = eval(self.mylist)
                    logging.debug("Converted string to list")
                    self.mylist=temp
                except:
                    logging.error("mylist SAVE ERROR at ["+str(self.id)+"]: NOT ALLOWING to save string as list given: "+str(self.mylist))
                    ok_to_save=False
        now=datetime.datetime.now()
        the_now = str(now).split('.')
        fmt = '%Y-%m-%d %H:%M:%S'  # ie/  d1 = datetime.strptime('2010-01-01 17:31:22', fmt)
        self.timestamp = datetime.datetime.strptime(str(the_now[0]), fmt)
            
        # SAVE!
        if ok_to_save: super(dashydb, self).save(*args, **kwargs) # Call the "real" save() method.
        else:
            logging.error("ERROR SAVING IN MODEL.PY!")
        
    def embedded_model_2dict(self,jindex):
        self.mytagtree_dict={}
        # Query
        self.mytagtree_dict={} 
        mytagtree=dashydb.objects.get(id=jindex).tagtree_model #Load one problem instance
        for entity in mytagtree:
            myelement=entity.element
            mydescription=entity.description
            self.mytagtree_dict[myelement]=mydescription
#            logging.info("--------------GOT2: "+str(myelement)+" and "+str(mydescription))
        
        return self.mytagtree_dict
    
    

class TagTreeDB(models.Model):
    tindex=models.CharField(max_length=500,default=0)
    now=datetime.datetime.now()
    element=models.CharField(max_length=30,default="",null=True,blank=True,primary_key=True)
    description=models.CharField(max_length=40,default="",null=True,blank=True,db_index=False)
    myspawn =fields.ListField(models.CharField(max_length=15),null=True,blank=True)
    
    def __unicode__(self):
        self.title="TagTree UniText MetaData"
        return self.title
   
    def __str__(self):
        self.title="TagTree Text"
        return self.title
    
    class Admin:
        pass
    
    
class RelationshipDB(models.Model):
    # Store relationship (multi-level) for given nodes
    from_id=models.CharField(max_length=100,blank=True) #Consider changing to long int (so can match against id)
    to_id=models.CharField(max_length=100,blank=True) #Consider changing to long int (so can match against id)
    many_id=fields.ListField(models.CharField(max_length=50),null=True,blank=True)
    type=models.CharField(max_length=15)
    category1=models.CharField(max_length=20)#Dec 8, 2012
    subtype=models.CharField(max_length=15)
    status=models.IntegerField(default=0)
    weight=models.FloatField(default=0)
    date=datetime.datetime.now()
    viewcount=models.IntegerField(default=0)
    directed=models.BooleanField() #Dec 8, 2012
    
    def to_dict(self):
        return dict([(p, unicode(getattr(self, p))) for p in self.properties()])
    
    def __unicode__(self):
        return self.link_id
   
    def __str__(self):
        return self.link_id

    class Admin:
        pass
    
    