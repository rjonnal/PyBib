from pybib import JournalList,BibtexBibliography

build_journal_db = False
if build_journal_db:
    jlist = JournalList()
    jlist.populate_from_csv(os.path.join(JOURNAL_LIST_DIR,'isi_html.csv'))
    jlist.populate_from_csv(os.path.join(JOURNAL_LIST_DIR,'jlist.csv'))
    jlist.populate_from_csv(os.path.join(JOURNAL_LIST_DIR,'additions.csv'),True)
    jlist.write_db(False)
    
bb = BibtexBibliography()
rebuild = False
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
