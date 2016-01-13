import csv
import sqlite3
import sys,os
from time import sleep
import difflib
import urllib2


JOURNAL_LIST_FILENAME = './journal_list/jlist.csv'
DATABASE_FILENAME = './db/pybib.db'
BIBTEX_FILENAME = './bibtex/bibliography_full.bib'
TITLE_KEY_FILENAME = './bibtex/longtitles.bib'
VALID_ENTRY_MINIMUM_LENGTH = 10

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



class JournalListISI:

    def __init__(self):
        pass

    def get_html(self):
        template = 'http://www.efm.leeds.ac.uk/~mark/ISIabbr/%s_abrvjt.html'
        letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        outdir = './journal_list/isi_html'
        for letter in letters:
            url = template%letter
            response = urllib2.urlopen('http://pythonforbeginners.com/')
            print letter,response.info()
            html = response.read()
            outfn = os.path.join(outdir,'%s.html'%letter)
            with open(outfn,'w') as fid:
                fid.write(html)
            response.close()  # best practice to close the file

    
        
class JournalList:

    def __init__(self,filename):
        self.journals = []
        self.conn = sqlite3.connect(DATABASE_FILENAME)
        c = self.conn.cursor()

        c.execute('''DROP TABLE IF EXISTS journals''')
        c.execute('''CREATE TABLE journals (title text, abbreviated_title text, publisher text, latest_issue text, earliest_volume text, open_access text, url text)''')

        self.all_titles = []
        self.long_titles = []
        self.short_titles = []
        
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
                    self.all_titles.append(title)
                    self.all_titles.append(abbreviated_title)
                    self.short_titles.append(abbreviated_title)
                    self.long_titles.append(title)
                    
                    self.journals.append(journal)
        self.conn.commit()

    def get_close_matches(self,test_string,n=3,cutoff=0.6):
        return difflib.get_close_matches(test_string,self.all_titles)


class BibtexString:

    def __init__(self,string):
        self.string = string
        self.substring = string
        self.original_length = len(self.string)

    def has_chunks(self):
        return len(self.substring)>VALID_ENTRY_MINIMUM_LENGTH
    
    def get_chunk(self):
        out = ''
        at_idx = self.substring.find('@')
        self.substring = self.substring[at_idx:]
        open_bracket_idx = self.substring.find('{')
        score = 1
        position = open_bracket_idx+1
        while score>0 and len(self.substring)>1:
            try:
                if self.substring[position]=='}':
                    score = score - 1
                if self.substring[position]=='{':
                    score = score + 1
                position = position + 1
            except IndexError as e:
                break
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
                temp = item.split('=')
                key = temp[0]
                val = '='.join(temp[1:])
                out[key] = val.replace('{','').replace('}','')
        return out
        
    
class BibtexBibliography:

    def __init__(self,filename):
        self.database = []
        with open(filename,'rb') as f:
            bibtex_string = f.read()
        bs = BibtexString(bibtex_string)
        while bs.has_chunks():
            entry = bs.process_chunk()
            self.database.append(entry)

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

        for idx,item in enumerate(self.database):
            try:
                journal = item['journal']
                if journal in keys:
                    item['journal'] = self.string_database[journal]
            except Exception as e:
                continue
jlist = JournalListISI()
jlist.get_html()
sys.exit()
jlist = JournalList(JOURNAL_LIST_FILENAME)
bb = BibtexBibliography(BIBTEX_FILENAME)
bb.replace_strings(TITLE_KEY_FILENAME,'./bibtex/test.bib')

for item in bb.database:
    try:
        matches = jlist.get_close_matches(item['journal'])
        print item,matches
    except KeyError as e:
        print e
    print

