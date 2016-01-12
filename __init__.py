import csv
import sqlite3
class Journal:

    def __init__(self,title,abbreviated_title,publisher,
                 latest_issue,earliest_volume,open_access,url):
        self.title = title
        self.abbreviated_title = abbreviated_title
        self.publisher = publisher
        self.latest_issue = latest_issue
        self.earliest_volume = earliest_volume
        self.open_access = open_access
        self.url = url

    def __str__(self):
        return '%s (%s), published by %s (%s)'%(self.title,self.abbreviated_title,self.publisher,self.url)


    def __repr__(self):
        return self.abbreviated_title
    
class JournalList:

    def __init__(self,filename):
        self.journals = []
        with open(filename,'rb') as csvfile:
            reader = csv.reader(csvfile)
            header_done = False
            for row in reader:
                if not header_done:
                    header = row
                    header_done = True
                else:
                    title = row[0]
                    abbreviated_title = row[1]
                    publisher = row[4]
                    latest_issue = row[6]
                    earliest_volume = row[7]
                    open_access = row[9]
                    url = row[12]
                    journal = Journal(title,abbreviated_title,publisher,
                                      latest_issue,earliest_volume,open_access,url)

                    self.journals.append(journal)
        print self.journals
                    
journal_list_filename = './journal_list/jlist.csv'
jlist = JournalList(journal_list_filename)
