import csv
import sqlite3
import sys,os

JOURNAL_LIST_FILENAME = './journal_list/jlist.csv'
DATABASE_FILENAME = './db/pybib.db'
BIBTEX_FILENAME = './bibtex/bibliography.bib'
TITLE_KEY_FILENAME = './bibtex/longtitles.bib'

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

    def db_put(self,cursor):
        cursor.execute('''INSERT INTO journals VALUES(?,?,?,?,?,?,?)''',(self.title,self.abbreviated_title,self.publisher,self.latest_issue,self.earliest_volume,self.open_access,self.url))
    
class JournalList:

    def __init__(self,filename):
        self.journals = []
        self.conn = sqlite3.connect(DATABASE_FILENAME)
        c = self.conn.cursor()

        c.execute('''DROP TABLE IF EXISTS journals''')
        c.execute('''CREATE TABLE journals (title text, abbreviated_title text, publisher text, latest_issue text, earliest_volume text, open_access text, url text)''')
            
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
                    journal.db_put(c)

                    self.journals.append(journal)
        self.conn.commit()



class BibtexString:

    def __init__(self,string):
        self.string = string
        self.substring = string

    def get_chunk(self):
        out = ''
        at_idx = self.substring.find('@')
        self.substring = self.substring[at_idx:]
        open_bracket_idx = self.substring.find('{')+1
        score = 1
        position = open_bracket_idx
        while score>0:
            if self.substring[position]=='}':
                score = score - 1
            if self.substring[position]=='{':
                score = score + 1
            #print self.substring[position],score
            position = position + 1
        out = self.substring[:position]
        self.substring = self.substring[position:]
        return out

    def process_chunk(self):
        out = {}
        chunk = self.get_chunk()
        entry_type = chunk[chunk.find('@')+1:chunk.find('{')]
        out['entry_type'] = entry_type
        last_close_curly = len(chunk) - chunk[::-1].find('}')
        innards = chunk[chunk.find('{')+1:last_close_curly-1]

        # replace unquoted commas with '|^|^|'
        position = 0
        score = 0
        new_innards = ''
        while position<len(innards):
            if innards[position]==',':
                if score>0:
                    new_innards = new_innards + ','
                else:
                    new_innards = new_innards + '|^|^|'
            else:
                new_innards = new_innards + innards[position]
            if innards[position]=='{':
                score = score + 1
            if innards[position]=='}':
                score = score - 1
            position = position + 1

        temp = new_innards.split('|^|^|')
        action_items = []
        for item in temp:
            action_items.append(item.strip())

        for item in action_items:
            if item.find('=')==-1:
                out['tag'] = item
            else:
                key,val = item.split('=')
                out[key] = val[1:-1]
        return out
        
    
class BibtexBibliography:

    def __init__(self,filename):
        with open(filename,'rb') as f:
            bibtex_string = f.read()
        bs = BibtexString(bibtex_string)
        for k in range(100):
            print bs.process_chunk()

    def replace_strings(self,replacement_key_filename,output_filename):
        with open(replacement_key_filename,'rb') as f:
            bibtex_string = f.read()

        substring = bibtex_string
        idx = substring.lower().find('@string')
        self.string_database = {}
        while idx>-1:
            substring = substring[7:]
            open_curly_idx = substring.find('{')
            close_curly_idx = substring.find('}')
            item = substring[open_curly_idx+1:close_curly_idx]
            substring = substring[close_curly_idx+1:]
            idx = substring.lower().find('@string')
            key,val = item.split('=')
            val = val.replace('"','')
            self.string_database[key] = val

        keys = self.string_database.keys()
        print self.string_database.values()

        for idx,item in enumerate(self.database.entries):
            try:
                journal = item['journal']
                if journal in keys:
                    item['journal'] = self.string_database[journal]
            except Exception as e:
                continue
            
        out = bibtexparser.dumps(self.database)
        #print out
        #writer = bibtexparser.bwriter.BibTexWriter()
        #with open(output_filename, 'w') as bibfile:
        #    bibfile.write(writer.write(self.database))
    
#jlist = JournalList(JOURNAL_LIST_FILENAME)
bb = BibtexBibliography(BIBTEX_FILENAME)
#bb.replace_strings(TITLE_KEY_FILENAME,'./bibtex/test.bib')
