from flask import Flask
from flask import render_template, request, url_for
import os
import glob
import json
import datetime
import html
import re
from paraanno import text_processing as tp

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

DATADIR=os.environ["VIS_PICK_DATA"]
APP_ROOT=os.environ.get("VIS_PICK_ROOT","")


class Batch:
    def __init__(self, batchfile):
        self.batchfile = batchfile
        with open(batchfile) as f:
            self.data = json.load(f) #this is a list of document pairs to annotate
            if isinstance(self.data, list):
                # old version without movie level metadata
                # create metadata on the fly
                self.data = {"id": os.path.basename(batchfile),
                             "name": "",
                             "segments": self.data}
        self.new_data = [] # processed data for visualization
        self.read_batch() # fills in new_data

    def read_batch(self):
        for seg in self.data["segments"]:
            if "annotation" in seg: # those with sentence pairs picked
                self.new_data.append(self.read_seg(seg))
            else:
                self.new_data.append({"d1_text": seg["d1_text"],
                                      "d2_text": seg["d2_text"],
                                      "annotation": []})

    def read_seg(self, seg):
        d1_text = tp.process_txt(seg["d1_text"])
        d2_text = tp.process_txt(seg["d2_text"])
        processed_txt1 = tp.sanitize(tp.post_processing_txt(d1_text))
        processed_txt2 = tp.sanitize(tp.post_processing_txt(d2_text))
        mapping1 = tp.map_processed_text(d1_text.lower(), processed_txt1)
        mapping2 = tp.map_processed_text(d2_text.lower(), processed_txt2)
        annotations = [tuple(dp["txt"].split("\n")) for dp in seg["annotation"]]
        mapped_anns = [] # list of ((start_index_1, end_index1), (start_index_2, end_index_2))
        for seg1, seg2 in annotations:
            indices1 = tp.locate_segment_in_original_text(seg1, processed_txt1, mapping1)
            indices2 = tp.locate_segment_in_original_text(seg2, processed_txt2, mapping2)
            import sys
            if indices1==(0,0):
                print("NOT FOUND",self.batchfile,"seg1",seg1, processed_txt1, file=sys.stderr)
            elif indices1==(1,1):
                print("INDEX WRONG",self.batchfile,"seg1",seg1, processed_txt1, file=sys.stderr)
            else:
                print("SUCCESS")
            if indices2==(0,0):
                print("NOT FOUND",self.batchfile,"seg2",seg2, processed_txt2, file=sys.stderr)
            elif indices2==(1,1):
                print("INDEX WRONG",self.batchfile,"seg2",seg2, processed_txt2, file=sys.stderr)
            else:
                print("SUCCESS")

            mapped_anns.append((indices1, indices2))
        return {"d1_text": d1_text,
                "d2_text": d2_text,
                "annotation": mapped_anns}
    
    @property
    def get_anno_stats(self):
        extracted=0
        touched=0
        if "_r" in self.data["id"]: # new rounds
            for pair in self.data["segments"]:
                # not taking into account the candidates picked in the previous rounds
                if not pair["locked"] and "annotation" in pair and pair["annotation"]:
                    extracted+=len(pair["annotation"])
                    touched+=1
        else: # old rounds
            for pair in self.data["segments"]:
                if "annotation" in pair and pair["annotation"]:
                    extracted+=len(pair["annotation"])
                    touched+=1
        return (touched,extracted) #how many pairs touched, how many examples extracted total
    
    def get_update_timestamp(self):
        timestamps=[pair.get("updated") for pair in self.data["segments"] if "locked" in pair and not pair["locked"]]
        timestamps=[stamp for stamp in timestamps if stamp]
        timestamps = [datetime.datetime.fromisoformat(stamp) for stamp in timestamps]
        #print("TS",timestamps)
        if not timestamps:
            return "no updates"
        else:
            return max(timestamps).isoformat()

def read_batches():
    fnames = sorted(glob.glob(DATADIR+"/*.json"))
    files = {os.path.basename(f): Batch(f) for f in fnames}
    return files
         
def init():
    global all_batches
    all_batches = read_batches()

init()            

@app.route('/')
def batchlist():
    global all_batches
    batches = []
    for fname, b in all_batches.items():
        name = b.data["name"].replace("\\","")
        batches.append((name, b, os.path.basename(b.batchfile)))
    return render_template("index.html",
                           app_root=APP_ROOT,
                           batches=batches)

@app.route("/ann/<batchfile>")
def jobsinbatch(batchfile):
    global all_batches
    pairs = all_batches[batchfile].data["segments"]
    pairdata=[]
    for idx, pair in enumerate(pairs):
        text1 = all_batches[batchfile].data["segments"][idx]["d1_text"]
        text2 = all_batches[batchfile].data["segments"][idx]["d2_text"]
        pairdata.append((idx, text1[:100], text2[:100]))
    return render_template("doc_list_in_batch.html",
                           app_root=APP_ROOT,
                           batchfile=batchfile,
                           pairdata=pairdata)

@app.route("/ann/<batchfile>/<pairseq>")
def fetch_document(batchfile, pairseq):
    global all_batches
    pairseq = int(pairseq)

    text1 = all_batches[batchfile].new_data[pairseq]["d1_text"]
    text2 = all_batches[batchfile].new_data[pairseq]["d2_text"]
    annotation = all_batches[batchfile].new_data[pairseq]["annotation"]
    
    return render_template("doc.html",
                           app_root=APP_ROOT,
                           left_text=text1,
                           right_text=text2,
                           pairseq=pairseq,
                           batchfile=batchfile,
                           annotation=annotation,
                           is_last=(pairseq==len(all_batches[batchfile].data["segments"])-1))

