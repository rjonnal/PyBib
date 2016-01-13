import csv
import sqlite3
import sys,os
from time import sleep
import difflib
import urllib2
import distance

JOURNAL_LIST_FILENAME = './journal_list/jlist.csv'
DATABASE_FILENAME = './db/pybib.db'
BIBTEX_FILENAME = './bibtex/bibliography_full.bib'
TITLE_KEY_FILENAME = './bibtex/longtitles.bib'
VALID_ENTRY_MINIMUM_LENGTH = 10
ISI_HTML_DIR = './journal_list/isi_html'
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LOWER_CASE_WORDS = ['a', 'aboard', 'about', 'above', 'absent', 'across', 'after', 'against', 'along', 'alongside', 'amid', 'amidst', 'among', 'amongst', 'an', 'and', 'around', 'as', 'aslant', 'astride', 'at', 'athwart', 'atop', 'barring', 'before', 'behind', 'below', 'beneath', 'beside', 'besides', 'between', 'beyond', 'but', 'by', 'despite', 'down', 'during', 'except', 'failing', 'following', 'for', 'for', 'from', 'in', 'inside', 'into', 'like', 'mid', 'minus', 'near', 'next', 'nor', 'notwithstanding', 'of', 'off', 'on', 'onto', 'opposite', 'or', 'out', 'outside', 'over', 'past', 'per', 'plus', 'regarding', 'round', 'save', 'since', 'so', 'than', 'the', 'through', 'throughout', 'till', 'times', 'to', 'toward', 'towards', 'under', 'underneath', 'unlike', 'until', 'up', 'upon', 'via', 'vs.', 'when', 'with', 'within', 'without', 'worth', 'yet']

PARAMETER_PRIORITIES = {'entry_type':99, 'journal':85, 'tag':100, 'year':65, 'title':90, 'publisher':0, 'author':95, 'number':75, 'volume':80, 'pages':70, 'blurb':0, 'note':0, 'booktitle':0, 'organization':0, 'howpublished':0, 'editor':0, 'timestamp':0, 'owner':0, 'institution':0, 'month':0, 'nourl':0, 'abstract':0, 'keywords':0, 'location':0, '__markedentry':0, 'chapter':0, 'pii':0, 'doi':0, 'pmid':0, 'school':0, 'address':0, 'url':0, 'edition':0, 'city':0, 'issue':0}

ACRONYMNS = ['AO','OCT','SLO','AO-OCT','AO-SLO','AOSLO','AOOCT','SD-OCT','TD-OCT','SS-OCT','pvOCT']

class Journal:

    db_put_count = 1
    
    def __init__(self,long_title,short_title):
        self.long_title = long_title
        self.short_title = short_title

    def __str__(self):
        return self.short_title

    def __repr__(self):
        return self.short_title

    def db_put(self,cursor):
        print 'Adding %s to database (%d).'%(self,Journal.db_put_count),
        try:
            cursor.execute('''INSERT INTO journals VALUES(?,?)''',(self.long_title,self.short_title))
            Journal.db_put_count = Journal.db_put_count + 1
            print
        except sqlite3.IntegrityError as e:
            print e,'. Journal "%s" already exists.'%self
                
class JournalList:

    def __init__(self):
        self.journals = []
        self.long_titles = []
        self.short_titles = []
        self.conn = sqlite3.connect(DATABASE_FILENAME)

    def read_db(self):
        c = self.conn.cursor()
        for row in c.execute('SELECT * FROM journals ORDER BY long_title'):
            self.add(*row)
        
    def write_db(self):
        c = self.conn.cursor()

        c.execute('''DROP TABLE IF EXISTS journals''')
        c.execute('''CREATE TABLE journals (long_title TEXT PRIMARY KEY, short_title TEXT)''')
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
                    self.add(long_title,short_title,True)

    def populate_from_html(self,dirname):
        for letter in LETTERS:
            fid = open(os.path.join(dirname,'%s.html'%letter))
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
                self.add(long_title,short_title,True)
                
    def add(self,long_title,short_title,check_case=False):
        if check_case:
            long_title = self.title_case(long_title)
            short_title = self.title_case(short_title)
        journal = Journal(long_title,short_title)
        if not long_title in self.long_titles:
            self.short_titles.append(short_title)
            self.long_titles.append(long_title)
            self.journals.append(journal)
        
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
    

    def get_close_matches_short(self,test_string,n=5,cutoff=0.5):
        return self.get_scored_matches(test_string,self.short_titles,n,cutoff,True)

    def get_close_matches_long(self,test_string,n=5,cutoff=0.5):
        return self.get_scored_matches(test_string,self.long_titles,n,cutoff,True)

    def get_scored_matches(self,test_string,test_list,n,cutoff,ignore_case):
        candidates = difflib.get_close_matches(test_string,test_list,n=n,cutoff=cutoff)
        scores = []
        for candidate in candidates:
            if ignore_case:
                scores.append(1.0-distance.levenshtein(test_string,candidate,normalized=True))
            else:
                scores.append(1.0-distance.levenshtein(test_string.lower(),candidate.lower(),normalized=True))
        return zip(candidates,scores)
    


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
        entry_type = chunk[chunk.find('@')+1:chunk.find('{')].upper()
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
                key = temp[0].strip().lower()
                val = '='.join(temp[1:]).strip()
                if val[0]=='{' and val[-1]=='}':
                    val = val[1:-1]
                out[key] = val
        return out
        
    
class BibtexBibliography:

    def __init__(self):
        self.conn = sqlite3.connect(DATABASE_FILENAME)

        self.database = []
        self.entry_types = []
        self.parameters = []
        self.tags = []


    def populate_from_bibtex(self,filename):
        with open(filename,'rb') as f:
            bibtex_string = f.read()
        bs = BibtexString(bibtex_string)
        while bs.has_chunks():
            entry = bs.process_chunk()

            while entry['tag'] in self.tags:
                entry['tag'] = entry['tag'] + '_'
                
            self.database.append(entry)
            self.add_schema(entry)

    def add_schema(self,entry):
            self.tags.append(entry['tag'])
            
            et = entry['entry_type']
            if not et in self.entry_types:
                self.entry_types.append(et)
            ekeys = entry.keys()
            for ekey in ekeys:
                if not ekey.lower() in self.parameters:
                    self.parameters.append(ekey.lower())

    def read_db(self):
        c = self.conn.cursor()
        keys = []
        for row in c.execute('PRAGMA table_info(bibliography)'):
            keys.append(row[1])
        for row in c.execute('SELECT * FROM bibliography ORDER BY tag'):
            entry = {}
            for key,value in zip(keys,row):
                entry[key] = value
            self.database.append(entry)
            self.add_schema(entry)
            
    def write_db(self):
        c = self.conn.cursor()
        # look through the parameters of the existing entries to assemble some SQL
        priorities = []
        pkeys = PARAMETER_PRIORITIES.keys()
        for param in self.parameters:
            if param in pkeys:
                priorities.append(PARAMETER_PRIORITIES[param])
            else:
                priorities.append(0)

        # sort params by priority, for sensible ordering in db
        params = [param for (priority,param) in sorted(zip(priorities,self.parameters))][::-1]
        sql = '(%s TEXT PRIMARY KEY, '%params[0]
        params = params
        for param in params[1:]:
            sql = sql + '%s TEXT, '%param
        sql = sql[:-2]
        sql = sql + ')'

        n_params = len(params)
        qmarks = '('+'?,'*(n_params-1)+'?)'
        
        c.execute('''DROP TABLE IF EXISTS bibliography''')
        c.execute('''CREATE TABLE bibliography'''+sql)

        for entry in self.database:
            values = []
            for param in params:
                try:
                    values.append(unicode(entry[param]))
                except Exception as e:
                    values.append('')
            command = '''INSERT INTO bibliography VALUES'''+qmarks
            try:
                c.execute(command,values)
            except sqlite3.IntegrityError as e:
                print 'Tag %s already exists in bibliography.'%(entry['tag']),params[0]
        self.conn.commit()

                    
    def replace_strings(self,replacement_key_filename):
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

    def clean_journal_titles(self,use_long_titles=True):
        jlist = JournalList()
        jlist.read_db()
        for idx,entry in enumerate(self.database):
            try:
                if use_long_titles:
                    matches = jlist.get_close_matches_long(entry['journal'],n=1)
                else:
                    matches = jlist.get_close_matches_short(entry['journal'],n=1)
            except KeyError as e:
                pass

            if len(matches):
                score = [y for x,y in matches][0]
                new_journal = [x for x,y in matches][0]
                if .95<score<1.0:
                    print 'Item %d of %d.'%(idx+1,len(self.database)),'%s -> %s.'%(entry['journal'],new_journal)
                    entry['journal'] = new_journal
                else:
                    pass
            
bb = BibtexBibliography()
bb.populate_from_bibtex(BIBTEX_FILENAME)
bb.replace_strings(TITLE_KEY_FILENAME)
bb.clean_journal_titles()
bb.write_db()

