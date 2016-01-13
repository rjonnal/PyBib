import csv
import sqlite3
import sys,os
from time import sleep
import difflib
import urllib2
from bs4 import BeautifulSoup

JOURNAL_LIST_FILENAME = './journal_list/jlist.csv'
DATABASE_FILENAME = './db/pybib.db'
BIBTEX_FILENAME = './bibtex/bibliography_full.bib'
TITLE_KEY_FILENAME = './bibtex/longtitles.bib'
VALID_ENTRY_MINIMUM_LENGTH = 10
ISI_HTML_DIR = './journal_list/isi_html'
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LOWER_CASE_WORDS = ['a', 'aboard', 'about', 'above', 'absent', 'across', 'after', 'against', 'along', 'alongside', 'amid', 'amidst', 'among', 'amongst', 'an', 'and', 'around', 'as', 'aslant', 'astride', 'at', 'athwart', 'atop', 'barring', 'before', 'behind', 'below', 'beneath', 'beside', 'besides', 'between', 'beyond', 'but', 'by', 'despite', 'down', 'during', 'except', 'failing', 'following', 'for', 'for', 'from', 'in', 'inside', 'into', 'like', 'mid', 'minus', 'near', 'next', 'nor', 'notwithstanding', 'of', 'off', 'on', 'onto', 'opposite', 'or', 'out', 'outside', 'over', 'past', 'per', 'plus', 'regarding', 'round', 'save', 'since', 'so', 'than', 'the', 'through', 'throughout', 'till', 'times', 'to', 'toward', 'towards', 'under', 'underneath', 'unlike', 'until', 'up', 'upon', 'via', 'vs.', 'when', 'with', 'within', 'without', 'worth', 'yet']

class Journal:

    def __init__(self,long_title,short_title):
        self.long_title = long_title
        self.short_title = short_title

    def __str__(self):
        return self.short_title

    def __repr__(self):
        return self.short_title

    def db_put(self,cursor):
        cursor.execute('''INSERT INTO journals VALUES(?,?)''',(self.long_title,self.short_title))
                
class JournalList:

    def __init__(self):
        self.journals = []
        self.long_titles = []
        self.short_titles = []

    def write_db(self):
        self.conn = sqlite3.connect(DATABASE_FILENAME)
        c = self.conn.cursor()

        c.execute('''DROP TABLE IF EXISTS journals''')
        c.execute('''CREATE TABLE journals (title text, abbreviated_title text)''')
        for j in self.journals:
            j.db_put(self.conn.cursor())
        self.conn.commit()
        
    def get_html(self):
        template = 'http://www.efm.leeds.ac.uk/~mark/ISIabbr/%s_abrvjt.html'
        for letter in LETTERS:
            url = template%letter
            response = urllib2.urlopen(url)
            print letter,response.info()
            html = response.read()
            outfn = os.path.join(ISI_HTML_DIR,'%s.html'%letter)
            with open(outfn,'w') as fid:
                fid.write(html)
            response.close()

    def populate_from_csv(self,filename):
        with open(filename,'rb') as csvfile:
            reader = csv.reader(csvfile)
            header_done = False
            for row in reader:
                if not header_done:
                    header = row
                    header_done = True
                else:
                    long_title = row[0]
                    short_title = row[1]
                    journal = Journal(long_title,short_title)
                    self.add(long_title,short_title)

    def populate_from_html(self):
        for letter in LETTERS:
            fid = open(os.path.join(ISI_HTML_DIR,'%s.html'%letter))
            html = fid.read()
            fid.close()
            while len(html)>VALID_ENTRY_MINIMUM_LENGTH:
                dtidx = html.find('<DT>')
                if dtidx==-1:
                    break
                html = html[dtidx+4:]
                nlidx = html.find('\n')
                long_title = html[:nlidx].strip()
                ddidx = html.find('<DD>')
                if ddidx==-1:
                    break
                html = html[ddidx+4:]
                nlidx = html.find('\n')
                short_title = html[:nlidx].strip()
                self.add(long_title,short_title)
                
    def add(self,long_title,short_title):
        long_title = self.title_case(long_title)
        short_title = self.title_case(short_title)
        journal = Journal(long_title,short_title)
        self.short_titles.append(short_title)
        self.long_titles.append(long_title)
        self.journals.append(journal)
        print journal
        
    def title_case(self,string):
        word_list = string.split(' ')
        output = [word_list[0].title()]
        last_colon = False
        for word in word_list[1:-1]:
            word = word.strip()
            if last_colon:
                output.append(word.title())
            elif word.lower() in LOWER_CASE_WORDS:
                output.append(word.lower())
                continue
            else:
                output.append(word.title())
            try:
                last_colon = word.strip()[-1]==':'
            except:
                last_colon = False
        output.append(word_list[-1].title())
        return ' '.join(output)
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

jlist = JournalList()
jlist.populate_from_html()
jlist.write_db()
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

