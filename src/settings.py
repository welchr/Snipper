#!/usr/bin/env/python

#===============================================================================
# This file is part of the Snipper program. 
# 
# Copyright (C) 2010 Ryan Welch
# 
# Snipper is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Snipper is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#===============================================================================

from ConfigParser import ConfigParser
from verboseparser import VerboseParser
from optparse import SUPPRESS_HELP
from textwrap import *
from constants import *
from util import *
from distutils.dir_util import mkpath
import sys
import os
import os.path as path
import re
import platform
import __builtin__

def parseTerms(term_string):
  terms = [];
  for term in term_string.split(","):
    term = term.strip();
    if term == "":
      continue;
    else:
      terms.append(term);
  
  return terms;

# Extract a set of SNPs from a file. 
# Returns: a set of SNPs
def parseSNPFile(absolute):
  if not os.path.isfile(absolute):
    raise Exception, "Could not find file: " + str(absolute);

  snps = set();

  f = open(absolute);
  snp_pattern = re.compile("rs(\d+)");
  snp1g_pattern = re.compile(r"\bchr(\d+?)\:(\d+)\b");
  for line in f:
    elements = line.split();
    for e in elements: 
      match = snp_pattern.findall(e);
      if match != None:
        for digits in match:
          snps.add("rs" + str(digits));
      
      match = snp1g_pattern.findall(e);
      if match != None:
        for tup in match:
          snps.add("chr%s:%s" % tup);

  f.close();

  return snps;

# Extract a list of gene symbols from a file. 
# Symbols must be separated by whitespace. 
def parseGeneFile(absolute):  
  if not os.path.isfile(absolute):
    raise Exception, "Could not find file: " + str(absolute);
  
  symbols = set();

  f = open(absolute);
  for line in f:
    elements = line.split();
    for e in elements:
      symbols.add(e.upper());
  f.close();

  return symbols;

# Pull out genes, SNPs, and genomic regions from a file. 
def parseGenericFile(file):
  if not os.path.isfile(file):
    raise Exception, "Could not find file: " + str(absolute);
  
  genes = set();
  snps = set();
  regions = set();
  
  f = open(file,"rU");
  for line in f:
    if line.strip() == "":
      continue;
    
    chunks = line.split();
    for e in chunks:
      if "rs" in e:
        snps.add(e);
      elif "chr" in e:
        if "-" in e:
          regions.add( ChromRegion.from_str(e) );
        else:
          snps.add(e);
      else:
        genes.add(e);
  
  f.close();
  
  return {'genes':genes,'snps':snps,'regions':regions};

# Pulls out regions from a string of the form: 
# chr4:1914-20104,chr8:939-93939,chrX:11738-234050
def parseRegions(regions_string):
  regions = set();
  for chunk in regions_string.split(","):
    chunk = chunk.strip();
    (chrom,pos_chunk) = chunk.split(":");
    
    chr = chrom2chr(chrom);
    (start,end) = pos_chunk.split("-");
    
    # Get rid of commas in numbers like 1,737,939
    start = start.replace(",","");
    end = end.replace(",","");
    
    try:
      chr = int(chr);
      start = int(start);
      end = int(end);
    except:
      raise ValueError, "Bad region string: (chr=%s,start=%s,end=%s)" % (str(chr),str(start),str(end));
    
    regions.add( ChromRegion(chr,start,end) );
  
  return regions;

def convertFlank(flank):
  iFlank = None;

  try:
    iFlank = int(flank);
    return iFlank;
  except:
    pass;

  p = re.compile("(.+)(kb|KB|Kb|kB|MB|Mb|mb|mB)")
  match = p.search(flank);
  if match:
    digits = match.groups()[0];
    suffix = match.groups()[1];

    if suffix in ('kb','KB','Kb','kB'):
      iFlank = float(digits)*1000;
    elif suffix in ('MB','Mb','mb','mB'):
      iFlank = float(digits)*1000000;

    iFlank = int(round(iFlank));

  return iFlank;

def findRelative(file):
  full_path = None;
  
  # Find the root, using the script's location. 
  start_loc = os.path.realpath(sys.argv[0]);
  script_dir = None;
  if os.path.isdir(start_loc):
    script_dir = start_loc;
  else:
    script_dir = os.path.dirname(start_loc);
  root_dir = os.path.join(script_dir,"../");
  
  # If the file to find has a path, it means it is a path relative
  # to the root. We need to attach that path to the root. 
  (file_path,file_name) = os.path.split(file);
  if file_path != "":
    root_dir = os.path.abspath(os.path.join(root_dir,file_path));
  
  if file_name == "" or file_name == None:
    if os.path.exists(root_dir):
      full_path = root_dir;
  else:
    temp_path = os.path.join(root_dir,file_name);
    if os.path.exists(temp_path):
      full_path = temp_path;
  
  return full_path;

# Find snipper config file. 
# It will search in these places, in this order: 
# 1) Attempt to find in directory of wherever snipper.py is being run from. 
# 2) Check SNIPPER_PATH environment variable. 
# 3) Check the current working directory. 
# The file MUST be called "snipper.conf"
def findConfigFile():
  # Check the directory relative to where the script is being run. 
  script_dir = os.path.abspath(os.path.dirname(sys.argv[0]));
  script_dir_conf = os.path.join(script_dir,'../conf/snipper.conf');
  if os.path.isfile(script_dir_conf):
    return script_dir_conf;

  # Now try SNIPPER_PATH environment variable. 
  environ_dir = os.environ.get('SNIPPER_PATH');
  if environ_dir != None:
    environ_dir_conf = os.path.join(environ_dir,'snipper.conf');
    if os.path.isfile(environ_dir_conf):
      return environ_dir_conf;

  # Last ditch resort..
  cur_dir = os.getcwd();
  cur_dir_conf = os.path.join(cur_dir,'snipper.conf');
  if os.path.isfile(cur_dir_conf):
    return cur_dir_conf;

  # If we're still here, no good moose!
  dirs = [str(i) for i in (script_dir,environ_dir,cur_dir)];
  err_msg = "Could not find snipper.conf file - check documentation. I tried looking in: %s" % str(dirs);
  raise RuntimeError, err_msg;

# Class to keep track of program settings. 
class Settings(object):
  def __init__(self):
    self.snpset = set();            # set of SNPs
    self.genes = set();             # set of genes
    self.regions = set();           # list of chromosomal regions
    self._distance = 250000;         # distance to search near SNPs
    self._num_genes = 9999;          # number of genes to return per SNP
    self.terms = set();             # search terms
    self.omim = True;               # use OMIM?
    self.pubmed = True;             # search pubmed?
    self._pnum = 10;                 # number of pubmed articles to return
    self.per_term = False;          # complicated, see help for info
    self.gene_rif = True;           # use gene rifs?
    self.scandb = True;             # search scandb for eqtls?
    self._scandb_pval = 0.0001;      # p-value threshold to be called an eQTL
    self.mimi = True;               # search MiMi for interactions between genes?
    self.overwrite = True;         # overwrite directory if exists already
    self.warn_overwrite = True;     # warn before overwriting directory
    self.db_file = None;            # database file for snp positions & genes
    self._build = None;              # human genome build for snp/gene positions
    self.valid_builds = set();      # builds available for use (conf file)
    self.console = False;

    self.conf = findConfigFile();
    self.getConfigFile(self.conf);

    if 'windows' in platform.system().lower():
      if len(sys.argv) > 1:
        self.outdir = os.path.join(os.getcwd(),"snipper_report")
      else:
        self.outdir = os.path.join(os.environ['USERPROFILE'],"Desktop","snipper_report");
    else:
      self.outdir = os.path.join(os.getcwd(),"snipper_report") ; # output directory
    
    try:
      if _SNIPPER_DEBUG: 
        self.write();
    except:
      pass

  def _get_dist(self):
    return self._distance;

  def _set_dist(self,value):
    x = convertFlank(value);
    if x <= 0:
      raise ValueError, "Error: distance must be positive and non-zero";
    
    self._distance = x;
  
  def _get_num_genes(self):
    return self._num_genes;
  
  def _set_num_genes(self,value):
    x = int(value);
    if x <= 0:
      raise ValueError, "Error: number of genes must be positive and non-zero";
    
    self._num_genes = x;
  
  def _get_pnum(self):
    return self._pnum;
  
  def _set_pnum(self,value):
    x = int(value);
    if x < 0:
      raise ValueError, "Error: number of PubMed articles must be non-zero";
  
    self._pnum = x;
  
  def _get_scandb_pval(self):
    return self._scandb_pval;
  
  def _set_scandb_pval(self,value):
    x = float(value);
    if x < 0 or x > 1:
      raise ValueError, "Error: SCAN p-value threshold must be between 0 and 1";
    
    self._scandb_pval = x;
  
  def _get_build(self):
    return self._build;
  
  def _set_build(self,value):
    self.checkBuild(value);
    self.getDB(value);
    self._build = value;
  
  build = property(_get_build,_set_build);
  scandb_pval = property(_get_scandb_pval,_set_scandb_pval);
  pnum = property(_get_pnum,_set_pnum);
  num_genes = property(_get_num_genes,_set_num_genes);
  distance = property(_get_dist,_set_dist);

  # Pull out genes, SNPs, and genomic regions from a file. 
  def parseGenericFile(self,file):
    if not os.path.isfile(file):
      raise Exception, "Could not find file: " + str(absolute);
    
    f = open(file,"rU");
    for line in f:
      self.parseGenericString(line);
    
    f.close();
    
  def parseGenericString(self,s):
    if s.strip() == "":
      return;
    
    chunks = s.split();
    for e in chunks:
      if "rs" in e:
        self.snpset.add(e);
      elif "chr" in e:
        if "-" in e:
          self.regions.add( ChromRegion.from_str(e) );
        else:
          self.snpset.add(e);
      else:
        self.genes.add(e);

  def parseTerms(self,term_string,delim="\n"):
    for term in term_string.split(delim):
      term = term.strip();
      if term == "":
        continue;
      else:
        self.terms.add(term);

  def getCmdLine(self):
    parser = VerboseParser();

    # Remember: default action is store, default type is string. 
    snp_help = "Lookup information for a list of SNPs - these must be separated by commas, surrounded by quotes (whitespace ignored.)\n\n" +\
      "Examples:\n" +\
      "-s \"rs1002227, rs35712349\"\n" +\
      "-s \"  rs1002227,    rs35712349\"\n" +\
      "-s \" rs1002227,rs35712349 \"\n" +\
      "-s \"rs1002227,rs35712349\"";
    parser.add_option("-s","--snp",dest="snp",help=snp_help);
    parser.add_option("-g","--gene",dest="gene",help="Lookup information for a list of gene symbols - these must be separated by commas, surrounded by quotes (whitespace ignored)");

    snpfile_help = "Provide a list of SNPs to lookup from a file. The file may have *ANY* format. \
  The program will pattern match rs### identifiers from your file.";
    parser.add_option("--snpfile",dest="snpfile",help=snpfile_help);

    genefile_help = "Provide a list of gene symbols in a file. This option unfortunately is not as lenient as --snpfile: you must put \
  each gene symbol on a separate line in the file.";
    parser.add_option("--genefile",dest="genefile",help=genefile_help);
    
    regions_help = "Provide a list of chromosomal regions. Genes and other "\
                   "elements inside these regions will be returned.\n"\
                   "Example:\n"\
                   " --regions \"chr4:19141-939393,chrX:9191-939393\"";
    parser.add_option("-r","--regions",help=regions_help);
    
    build_help = ("Human genome build to use for SNP positions and genes. "
                  "Snipper ships with hg19 by default. You can download "
                  "pre-built databases from our website, or build them "
                  "yourself using the bin/setup_snipper.py script.");
    parser.add_option("-b","--build",dest="build",help=build_help);

    dist_help = "Distance away from SNP to search, default is " + str(self.distance) + ". " +\
      "If a distance is specified, the program will return *ALL* genes within the distance you specify, not just the default of 1. " +\
      "To specify a new distance, but still only return 1 gene (or arbitrary number of genes), use -n <number>. " +\
      "Distances can be specified using a kb or mb suffix, or as a raw distance. Examples: 500kb, 0.5MB, 1.4MB, 834141.";
    parser.add_option("-d",dest="distance",help=dist_help,type="string");
    parser.add_option("-n",dest="num_genes",help="Number of genes to return per SNP, default is " + str(self.num_genes),type="int");
    
    terms_help = "Comma-delimited string of terms, enclosed in quotes, to use in searching the literature. \
  This will execute a search, per gene, for any of the search terms. For example:\n\
  \n\
  Genes: RB1, TCF7L2\n\
  Search terms: \"glucose,retinoblastoma\"\n\
  What happens: \n\
  -- Search literature for RB1 AND (glucose OR retinoblastoma)\n\
  -- Search literature for TCF7L2 AND (glucose OR retinoblastoma)";

    parser.add_option("--terms",dest="terms",help=terms_help); 
    parser.add_option("--no-generif",dest="gene_rif",action="store_true",default=False,help="Disable GeneRIFs.");
    parser.add_option("--no-scandb",dest="no_scandb",action="store_true",default=False,help="Disable use of ScanDB for eQTL information. Enabled by default.");
    parser.add_option("--scandb-pval",dest="scandb_pval",default=self.scandb_pval,help="P-value threshold for ScanDB eQTLs.");
    parser.add_option("--no-mimi",dest="mimi",action="store_true",default=False,help="Disable querying of MiMI database for interactions between genes near SNPs.");
    parser.add_option("--no-omim",dest="omim",action="store_true",default=False,help="Disable display and search of OMIM text.");
    parser.add_option("--no-pubmed",dest="pubmed",action="store_true",default=False,help="Disable searching PubMed.");
    parser.add_option("--papernum",dest="pnum",type="int",default=self.pnum,help="Number of papers to display, default is " + str(self.pnum));
    
    each_term_help = "When specified, the program will search each gene x searchterm pair, instead of lumping together search terms. \
  For example:\n\
  \n\
  Genes: RB1, TCF7L2\n\
  Search terms: \"glucose,retinoblastoma\"\n\
  What happens:\n\
  -- Search literature for RB1 AND glucose\n\
  -- Search literature for RB1 AND retinoblastoma\n\
  -- Search literature for TCF7L2 AND glucose\n\
  -- Search literature for TCF7L2 AND retinoblastoma\n\
  \n\
This is a much more in-depth search, at the cost of running time - NCIBI limits to 1 query / 3 seconds. \
If you have a very large set of genes and search terms, this can take a VERY long time to run!";
    
    parser.add_option("--each-term",dest="per_term",default=False,action="store_true",help=each_term_help);
    parser.add_option("--all",dest="all",action="store_true",default=True,help=SUPPRESS_HELP);
    parser.add_option("-o","--out",dest="outdir",default=self.outdir,help="Directory to use for storing output. This should be a directory that does not exist yet.");
    parser.add_option("--console",dest="console",action="store_true",default=self.console,help="Write results to console, instead of creating directory with HTML/text results.");
    parser.add_option("--debug",dest="debug",action="store_true",default=False,help=SUPPRESS_HELP);

    # Parse args. 
    (options,args) = parser.parse_args();

    # Was debug enabled?
    if options.debug:
      __builtin__._SNIPPER_DEBUG = True;
    else:
      __builtin__._SNIPPER_DEBUG = False;

    # If there are positional arguments, there was an error on the command line. 
    # Let them know the potential problem. 
    if len(args) > 0:
      print >> sys.stderr, "Error: positional arguments detected: " + str(args);
      print >> sys.stderr, "Most likely, you simply forgot to surround the entire argument in quotes."
      print >> sys.stderr, "Example: -g \"RB1, TCF7L2\" is correct, whereas -g \"RB1\" \"TCF7L2\" is wrong."
      sys.exit(1);

    # Console mode? 
    self.console = options.console;

    # Human genome build. 
    if options.build:
      self.build = options.build;

    # Get genes from command line (and file, if specified.) 
    if options.gene != None:
      self.genes = set([i.upper() for i in parseTerms(options.gene)]);
    if options.genefile != None:
      self.genes.update(parseGeneFile(options.genefile));

    # Get the set of SNPs. 
    if options.snp != None:
      self.snpset = set(parseTerms(options.snp));
    if options.snpfile != None:
      self.snpset.update(parseSNPFile(options.snpfile));

    # Get regions. 
    if options.regions != None:
      self.regions = parseRegions(options.regions);

    # Get list of search terms. 
    if options.terms != None:
      self.terms = parseTerms(options.terms);

    # HACK: If distance is specified, but num_genes is not,
    # then we want to search for all genes in that distance space. 
    # Set num_genes to a really really big number. :) 
    if options.distance != None:
      options.distance = convertFlank(options.distance);
      if options.num_genes != None:
        self.distance = options.distance;
        self.num_genes = options.num_genes;
      else:
        self.distance = options.distance;
        self.num_genes = 9999;
    else:
      if options.num_genes != None:
        self.num_genes = options.num_genes;

    # OMIM? 
    self.omim = not options.omim;

    # Pubmed?
    self.pubmed = not options.pubmed;
    self.pnum = options.pnum; 
    self.per_term = options.per_term;

    # GeneRIF? 
    self.gene_rif = not options.gene_rif;
    
    # ScanDB?
    if options.no_scandb:
      self.scandb = False;
    else:
      self.scandb_pval = float(options.scandb_pval);

    # MIMI?
    self.mimi = not options.mimi;
    
    # Check the output directory specified by the user.
    # It should not already exist. 
    if len(sys.argv) > 1 and not self.console:
      self.outdir = options.outdir;
      if os.path.exists(self.outdir):
        msg = "Error: output directory already exists: %s\n"\
              "Please rename or move this directory, or use "\
              "--output or -o to change the directory name." % self.outdir;
        sys.exit(msg);
      else:
        mkpath(self.outdir);

  # Check that we have info for the given build. 
  def checkBuild(self,build):
    parser = ConfigParser();
    parser.read(self.conf);
    
    # Check to see if user's requested build is in conf file. 
    if not parser.has_section(build):
      raise ValueError, ("Error: the human genome build you have requested does not "
                "exist on your system. Please use bin/setup_snipper.py to "
                "create a database file for this build, or download the "
                "database file from our website. "
              );

  def getDB(self,build):
    parser = ConfigParser();
    parser.read(self.conf);
    
    # Get database file information. 
    db_file = findRelative(parser.get(build,'db_file'));
    if db_file == None:
      raise ValueError, ("Error: could not find database file %s. Please check to make "
                "sure this file exists, or that the path is specified "
                "correctly in the conf file. " % db_file);
    elif not path.isfile(db_file):
      raise ValueError, ("Error: could not find database file %s. Please check to make "
                "sure this file exists, or that the path is specified "
                "correctly in the conf file. " % db_file);
    elif not os.access(db_file,os.R_OK):
      raise ValueError, ("Error: you do not have permissions to read the database "
                "file: %s. Please make sure this file is readable. " % db_file);
    else:
      self.db_file = db_file;

  # Load Snipper settings specified in conf file. 
  def getConfigFile(self,file):
    parser = ConfigParser();
    parser.read(file);

    # Get default build from config file. 
    try:
      self.build = parser.get('program','default_build');
    except:
      raise ValueError, ("Error: default_build does not exist in conf. Should be under section [program].")
    
    # Check build. 
    self.checkBuild(self.build);
    
    # Set DB file to default build. 
    self.getDB(self.build);

    # Set list of possible builds. 
    for sec in parser.sections():
      if "hg" in sec:
        self.valid_builds.add(sec);

  def __str__(self):
    s = [];
    s.append( "Snipper settings:");
    s.append( "-----------------");
    s.append( "Set of SNPs: " + str(self.snpset));
    s.append( "Set of genes: " + str(self.genes));
    s.append( "Set of regions: " + str([str(i) for i in self.regions]));
    s.append( "Distance: " + str(self.distance));
    s.append( "Num genes: " + str(self.num_genes));
    s.append( "Search terms: " + str(self.terms));
    s.append( "Use OMIM: " + str(self.omim));
    s.append( "Use Pubmed: " + str(self.pubmed));
    s.append( "Use SCAN: " + str(self.scandb));
    s.append( "Use GeneRIF: " + str(self.gene_rif));
    s.append( "SCAN p-value thresh: " + str(self.scandb_pval));
    s.append( "Num articles: " + str(self.pnum));
    s.append( "Per term: " + str(self.per_term));
    s.append( "Output directory: " + str(self.outdir));
    s.append( "Build: " + str(self.build));
    s.append( "Valid builds: " + str(self.valid_builds));
    s.append( "Database: " + str(self.db_file));
    return os.linesep.join(s);

  # Print a summary of all current settings. 
  def write(self,out=sys.stdout):
    print >> out, str(self);

if __name__ == "__main__":
  pass
  
  