import csv
import sqlite3
import sys,os
from time import sleep
import difflib
import urllib2
import distance

JOURNAL_LIST_DIR = './journal_list'
JOURNAL_LIST_FILENAME = './journal_list/jlist.csv'
REPLACEMENT_CACHE_DIR = os.path.join(JOURNAL_LIST_DIR,'journal_title_replacements')
try:
    os.makedirs(REPLACEMENT_CACHE_DIR)
except:
    pass
REPLACEMENT_CACHE_FILENAME = os.path.join(REPLACEMENT_CACHE_DIR,'journal_title_replacements.csv')
DATABASE_FILENAME = './db/pybib.db'
#BIBTEX_FILENAME = './bibtex/bibliography.bib'
BIBTEX_FILENAME = './bibtex/bibliography_full.bib'
TITLE_KEY_FILENAME = './bibtex/longtitles.bib'
VALID_ENTRY_MINIMUM_LENGTH = 10
ISI_HTML_DIR = './journal_list/isi_html'
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
LOWER_CASE_WORDS = ['a', 'aboard', 'about', 'above', 'absent', 'across', 'after', 'against', 'along', 'alongside', 'amid', 'amidst', 'among', 'amongst', 'an', 'and', 'around', 'as', 'aslant', 'astride', 'at', 'athwart', 'atop', 'barring', 'before', 'behind', 'below', 'beneath', 'beside', 'besides', 'between', 'beyond', 'but', 'by', 'despite', 'down', 'during', 'except', 'failing', 'following', 'for', 'for', 'from', 'in', 'inside', 'into', 'like', 'mid', 'minus', 'near', 'next', 'nor', 'notwithstanding', 'of', 'off', 'on', 'onto', 'opposite', 'or', 'out', 'outside', 'over', 'past', 'per', 'plus', 'regarding', 'round', 'save', 'since', 'so', 'than', 'the', 'through', 'throughout', 'till', 'times', 'to', 'toward', 'towards', 'under', 'underneath', 'unlike', 'until', 'up', 'upon', 'via', 'vs.', 'when', 'with', 'within', 'without', 'worth', 'yet']

PARAMETER_PRIORITIES = {'entry_type':99, 'journal':85, 'journal_abbreviated':84, 'tag':100, 'year':65, 'title':90, 'publisher':0, 'author':95, 'number':75, 'volume':80, 'pages':70, 'blurb':0, 'note':0, 'booktitle':0, 'organization':0, 'howpublished':0, 'editor':0, 'timestamp':0, 'owner':0, 'institution':0, 'month':0, 'nourl':0, 'abstract':0, 'keywords':0, 'location':0, '__markedentry':-1, 'chapter':0, 'pii':0, 'doi':0, 'pmid':0, 'school':0, 'address':0, 'url':0, 'edition':0, 'city':0, 'issue':0}

ACRONYMNS = ['AO','OCT','SLO','AO-OCT','AO-SLO','AOSLO','AOOCT','SD-OCT','TD-OCT','SS-OCT','pvOCT']
FIELDS_TO_IGNORE = ['abstract','keywords']
RETAG_EXISTING = False


def title_case_simple(self,string):
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
    
def title_case(self,string):
    string = string.replace('-',' ----- ')
    word_list = string.split(' ')
    one_word = len(word_list)==1
    if not word_list[0]==word_list[0].upper():
        output = [word_list[0].title()]
    else:
        output = [word_list[0]]
    last_colon = False
    for word in word_list[1:-1]:
        word = word.strip()
        if word==word.upper() and all([x.isalnum() for x in word]):
            output.append(word)
            continue
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
    if not one_word:
        if not word_list[-1]==word_list[-1].upper():
            output.append(word_list[-1].title())
        else:
            output.append(word_list[-1])
    return ' '.join(output).replace(' ----- ','-')


class Journal:

    db_put_count = 1
    
    def __init__(self,long_title,short_title):
        self.long_title = long_title
        self.short_title = short_title

    def __str__(self):
        return '%s / %s'%(self.long_title,self.short_title)

    def __repr__(self):
        return '%s / %s'%(self.long_title,self.short_title)

    def db_put(self,cursor,debug=False):
        if debug:
            print 'Adding %s to database (%d).'%(self,Journal.db_put_count),
        try:
            cursor.execute('''INSERT INTO journals VALUES(?,?)''',(self.long_title,self.short_title))
            Journal.db_put_count = Journal.db_put_count + 1
            if debug:
                print
        except sqlite3.IntegrityError as e:
            if debug:
                print e,'. Journal "%s" already exists.'%self
                
class JournalList:

    def __init__(self):
        self.journals = {}
        self.long_titles = {}
        self.short_titles = {}
        self.conn = sqlite3.connect(DATABASE_FILENAME)

    def read_db(self):
        c = self.conn.cursor()
        for row in c.execute('SELECT * FROM journals ORDER BY long_title'):
            self.add(*row)


    def write_csv(self,filename):
        with open(filename,'w') as csvfile:
            writer = csv.writer(csvfile)
            row = ['long_title','short_title']
            writer.writerow(row)
            for j in self.journals.values():
                writer.writerow([j.long_title,j.short_title])
        
    def write_db(self,debug=False):
        c = self.conn.cursor()

        c.execute('''DROP TABLE IF EXISTS journals''')
        c.execute('''CREATE TABLE journals (long_title TEXT PRIMARY KEY, short_title TEXT)''')
        for j in self.journals.values():
            j.db_put(self.conn.cursor(),debug=debug)
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

    def populate_from_csv(self,filename,debug=False):
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
                    if debug:
                        print long_title,short_title,long_title in self.long_titles
                    if not long_title in self.long_titles:
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
            long_title = title_case(long_title)
            short_title = title_case(short_title)
        journal = Journal(long_title,short_title)
        if not long_title in self.long_titles:
            self.short_titles[short_title.lower()] = short_title
            self.long_titles[long_title.lower()] = long_title
            self.journals[long_title.lower()]=journal

    def get_close_matches(self,test_string,n=5,cutoff=0.5):
        candidate_keys = difflib.get_close_matches(test_string.lower(),self.long_titles.keys(),n=n,cutoff=cutoff)
        candidates = []
        scores = []

        for candidate_key in candidate_keys:
            candidate = self.long_titles[candidate_key]
            candidates.append(candidate)
            scores.append(1.0-distance.levenshtein(test_string,candidate))

        return zip(candidates,scores)
    
    # def get_close_matches_short(self,test_string,n=5,cutoff=0.5):
    #     return self.get_scored_matches(test_string,self.short_titles,n,cutoff)

    # def get_close_matches_long(self,test_string,n=5,cutoff=0.5):
    #     return self.get_scored_matches(test_string,self.long_titles,n,cutoff)


    # def get_scored_matches(self,test_string,test_dict,n,cutoff):
    #     candidate_keys = difflib.get_close_matches(test_string,test_dict.keys(),n=n,cutoff=cutoff)
    #     candidates = []
    #     scores = []
        
    #     for candidate in candidate_keys:
    #         candidates.append(test_list[candidate]
            
    
    # def get_scored_matches_old(self,test_string,test_list,n,cutoff,ignore_case):
    #     candidates = difflib.get_close_matches(test_string,test_list,n=n,cutoff=cutoff)
    #     scores = []
    #     for candidate in candidates:
    #         if ignore_case:
    #             scores.append(1.0-distance.levenshtein(test_string,candidate,normalized=True))
    #         else:
    #             scores.append(1.0-distance.levenshtein(test_string.lower(),candidate.lower(),normalized=True))
    #     return zip(candidates,scores)
    


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
                if not key in FIELDS_TO_IGNORE:
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

            #while entry['tag'] in self.tags:
            #    entry['tag'] = entry['tag'] + '_'
                
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
                if not ekey.lower() in PARAMETER_PRIORITIES.keys():
                    PARAMETER_PRIORITIES[ekey.lower()] = 0    

    def read_db(self):
        c = self.conn.cursor()
        keys = []
        for row in c.execute('PRAGMA table_info(bibliography)'):
            keys.append(row[1])
        for row in c.execute('SELECT * FROM bibliography ORDER BY tag'):
            entry = {}
            for key,value in zip(keys,row):
                if len(value):
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

        # remove any negative-valued params
        npri = []
        npar = []
        for par,pri in zip(self.parameters,priorities):
            if pri>=0:
                npri.append(pri)
                npar.append(par)

        self.parameters = npar
        priorities = npri
                
        # sort params by priority, for sensible ordering in db
        params = [param for (priority,param) in sorted(zip(priorities,self.parameters))][::-1]
        sql = '(%s TEXT, '%params[0]
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
                    item['journal'] = self.string_database[journal].replace('\\','')
            except Exception as e:
                continue


    def csv_to_dict(self,filename):
        out = {}
        with open(filename,'rb') as fid:
            reader = csv.reader(fid)
            for row in reader:
                out[row[0]] = row[1:]
        return out


    def dict_to_csv(self,d,filename):
        keys = d.keys()
        with open(filename,'w') as fid:
            writer = csv.writer(fid)
            for k in keys:
                writer.writerow([k]+d[k])

    def row_to_csv(self,row,filename):
        if not os.path.exists(filename):
            with open(filename, 'a'):
                os.utime(filename, None)
        with open(filename,'a') as fid:
            writer = csv.writer(fid)
            writer.writerow(row)
            
    def clean_journal_titles(self,use_cache=True,debug=False):
        cache = {}
        if not os.path.exists(REPLACEMENT_CACHE_FILENAME):
            use_cache = False
        if use_cache:
            cache = self.csv_to_dict(REPLACEMENT_CACHE_FILENAME)
        
        jlist = JournalList()
        jlist.read_db()

        self.parameters.append('journal_abbreviated')

        for idx,entry in enumerate(self.database):
            if not 'journal' in entry.keys():
                continue
            
            cache_keys = cache.keys()
            old_title = entry['journal']

            # try to add a key for a short title:
            key = old_title.lower()
            try:
                entry['journal_abbreviated'] = jlist.journals[old_title.lower()].short_title
            except KeyError as ke:
                entry['journal_abbreviated'] = old_title

            
            if old_title in cache_keys:
                matches = [(cache[old_title][0],float(cache[old_title][1]))]
                cache_string = '(from cache)'
            else:
                matches = jlist.get_close_matches(old_title,n=3)
                cache_string = '(fresh match)'

            if len(matches):
                score = [y for x,y in matches][0]
                new_title = [x for x,y in matches][0]
                
                if not old_title in cache_keys:
                    self.row_to_csv([old_title,new_title,score],REPLACEMENT_CACHE_FILENAME)
                    cache[old_title] = [new_title,score]
                if debug:
                    print 'Item %d of %d.'%(idx+1,len(self.database))
                    print '\t',matches,cache_string
                if .9<score<1.0:
                    entry['journal'] = new_title
                    if debug:
                        print '\tREPLACING %s -> %s.'%(entry['journal'],new_title)
                        print
                else:
                    if debug:
                        print

    def to_bibtex(self,abbreviated=False,N=None):
        if N is None:
            N = len(self.database)
        output = u''
        for original_entry in self.database[:N]:
            entry = {}
            for key in original_entry.keys():
                entry[key] = original_entry[key]
            keys = entry.keys()
            if abbreviated:
                try:
                    entry['journal'] = entry['journal_abbreviated']
                    keys.remove('journal_abbreviated')
                except:
                    pass
            else:
                try:
                    keys.remove('journal_abbreviated')
                except:
                    pass
                
            keys.remove('entry_type')
            keys.remove('tag')
            keys = sorted(keys,key=lambda x: PARAMETER_PRIORITIES[x])[::-1]
            entry_type = entry['entry_type']
            tag = entry['tag']
            #output = output = output + u'@%s{%s,\n'%(entry_type,tag)
            to_add = '@%s{%s,\n'%(entry_type,tag)
            to_add = to_add.encode('utf-8','replace')
            output = output = output + to_add
            for key in keys:
                to_add = '\t%s={%s},\n'%(key,entry[key])
                to_add = to_add.encode('utf-8','replace')
                output = output + to_add
            output = output[:-2]+u'}\n\n'
        output = self.escape(output)
        return output

    def escape(self,text,chars='&'):
        output = text
        for c in chars:
            output = output.replace(c,'\%s'%c)
        return output
        
    def fix_tag_case(self):
        for entry in self.database:
            entry['tag'] = entry['tag'].lower()

    def fix_tag_logic(self,debug=False):
        existing_tags = []
        for entry in self.database:
            if debug:
                print 'working on %s'%entry

            if 'forced_tag' in entry.keys():
                entry['tag'] = entry['forced_tag']
                continue
                
            try:
                title = entry['title']
            except:
                try:
                    title = entry['booktitle']
                except:
                    continue

            term_list = title.replace('-',' ').split(' ')
            #title_term = term_list[0]
            
            for term in term_list:
                if not term.lower() in LOWER_CASE_WORDS:
                    title_term = term
                    break

            title_term = title_term.lower()
            title_term = ''.join(e for e in title_term if e.isalnum())
                
            try:
                author = entry['author']
            except:
                continue

            # print 'author',author
            author = author.replace('{','').replace('}','')
            author_list = author.split(' and ')
            # print 'author_list',author_list
            first_author = author_list[0]
            # print 'first_author',first_author
            # print 'comma?',first_author.find(',')

            first_author = first_author.lower()
            first_author = first_author.replace(', jr','').replace(',jr','').replace('jr','')
            first_author = first_author.strip()

            if first_author.find(',')>-1:
                author_term = first_author.split(',')[0]
            else:
                author_term = first_author.split(' ')[-1]
            
            author_term = ''.join(e for e in author_term if e.isalnum())
            
            try:
                year = entry['year'].replace(' ','')
            except:
                year = '0000'

            new_tag = '%s%s%s'%(author_term,year,title_term)


            if RETAG_EXISTING:
                while new_tag in existing_tags:
                    if debug:
                        print '\t%s is a duplicate'%new_tag
                        print '\t',[x for x in self.database if x['tag']==new_tag]
                    new_tag = new_tag + '_'
                    
            entry['tag'] = new_tag
            existing_tags.append(new_tag)
            if debug:
                print
            # print new_tag
            # continue
            # tag = entry['tag']
            # existing_tags = [x['tag'] for x in self.database]
            
            # while new_tag in existing_tags:
            #     if debug:
            #         print '\t%s is a duplicate'%new_tag
            #         print '\t',[x for x in self.database if x['tag']==new_tag]
            #     new_tag = new_tag + '_'

            # if debug:
            #     if not new_tag==tag:
            #         print '\ttag replaced: %s -> %s'%(tag,new_tag)    
            #         print

            # #if entry['author'].find('Cabrera')>-1:
            # print new_tag
            # entry['tag'] = new_tag

            
    def fix_josaa(self):
        for entry in self.database:
            try:
                if entry['journal'].strip()=='Journal of the Optical Society of America':
                    entry['journal']='Journal of the Optical Society of America A'
            except:
                pass

    def remove_brackets(self,debug=False):
        for entry in self.database:
            keys = entry.keys()
            for key in keys:
                val = entry[key].strip()
                if len(val):
                    if val[0]=='{' and val[-1]=='}':
                        newval = val[1:-1]
                        if debug:
                            print '%s -> %s'%(entry[key],newval)
                        entry[key] = newval

    def remove_newlines(self,debug=False):
        for entry in self.database:
            keys = entry.keys()
            for key in keys:
                val = entry[key].strip()
                if len(val):
                    newval = val.replace('\n',' ').replace('\r','')
                    if newval==val:
                        return
                    if debug:
                        print '%s -> %s'%(entry[key],newval)
                    entry[key] = newval

    
    def fix_title_case(self,debug=False):
        for entry in self.database:
            keys = entry.keys()
            fix_these = ['booktitle','journal']
            for key in fix_these:
                try:
                    oldval = entry[key]
                    newval = title_case(oldval)
                    if not oldval==newval:
                        entry[key] = newval
                        if debug:
                            print 'REPLACING: %s -> %s'%(oldval,newval)
                            print
                except Exception as e:
                    pass
                    
                
                
build_journal_db = False
if build_journal_db:
    jlist = JournalList()
    jlist.populate_from_csv(os.path.join(JOURNAL_LIST_DIR,'isi_html.csv'))
    jlist.populate_from_csv(os.path.join(JOURNAL_LIST_DIR,'jlist.csv'))
    jlist.populate_from_csv(os.path.join(JOURNAL_LIST_DIR,'additions.csv'),True)
    jlist.write_db(False)
    
bb = BibtexBibliography()
rebuild = True
if rebuild:
    bb.populate_from_bibtex(BIBTEX_FILENAME)
    bb.remove_brackets()
    bb.remove_newlines()
    bb.replace_strings(TITLE_KEY_FILENAME)
    bb.clean_journal_titles(debug=False)
    bb.fix_tag_logic(debug=False)
    bb.fix_title_case(debug=False)
    bb.write_db()

bb.read_db()
print bb.to_bibtex(abbreviated=True)
