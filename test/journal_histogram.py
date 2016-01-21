from pybib import JournalList,BibtexBibliography
from matplotlib import pyplot as plt
import numpy as np

bb = BibtexBibliography()
bb.read_db()

histogram_dict = {}

for entry in bb.database:
    try:
        abbr = entry['journal_abbreviated']
    except:
        pass

    if abbr in histogram_dict.keys():
        histogram_dict[abbr] = histogram_dict[abbr]+1
    else:
        histogram_dict[abbr] = 1


labels = histogram_dict.keys()
counts = []
for label in labels:
    counts.append(histogram_dict[label])

idx_vec = np.argsort(counts)[::-1]
counts = [counts[idx] for idx in idx_vec]
labels = [labels[idx] for idx in idx_vec]


fig = plt.figure(figsize=(20,5))
ax = plt.axes()

width = 0.8
rects = ax.bar(np.arange(len(counts))+width,counts,width)
ax.set_ylabel('Count')
plt.xticks(range(len(counts)),rotation='vertical')
ax.set_xticklabels(labels)
plt.subplots_adjust(bottom=.5)
#ax.set_xticks(ind + width)
#ax.set_xticklabels(('G1', 'G2', 'G3', 'G4', 'G5'))
plt.show()
