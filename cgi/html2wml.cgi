#! D:\programs\perl\bin\perl.exe
## D:\programs\perl\bin\perl.exe
# ########################################################################### #
# Html2Wml                                                                    #
# ========                                                                    #
# Author: Sebastien Aperghis-Tramoni <mad@maddingue.org>                      #
#                                                                             #
# This program converts HTML pages to WML pages.                              #
# See the documentation for more informations.                                #
#                                                                             #
# This program is available under the GNU General Public License.             #
#                                                                             #
# You can find the original archive of this program on the author's web site  #
#   http://www.maddingue.org/softwares/                                       #
#                                                                             #
# and on the web site of Html2Wml on SourceForge                              #
#   http://www.html2wml.org/                                                  #
#                                                                             #
# Copyright (c)2000, 2001, 2002 Sebastien Aperghis-Tramoni                    #
# ########################################################################### #

use strict;
use CGI;
use File::Basename;
use Getopt::Long;
use HTML::Parser;
use LWP::UserAgent;
use POSIX qw(isatty);
use Text::Template;
use URI;
use URI::URL;
use Time::HiRes qw(gettimeofday);

use vars qw($program $version);
$program = 'Html2Wml';
$version = '0.4.11';


# --------------------------------------------------------------------------- #
# Static configuration                                                        #
#                                                                             #
#   If you want to hard-code some parameters of Html2Wml, this is the         #
#   place to edit. Please check the documentation for more information.       #
#                                                                             #
my %defaults = (
    ## proxy settings
   'proxy-server'  =>  '', ## proxy server
    
    ## path to the WML compiler
   'wmlc'          =>  '/usr/local/bin/wmlc', 
    
    ## WML version and identifier
   'wmlvers'       =>  q|<!DOCTYPE wml PUBLIC "-//WAPFORUM//DTD WML 1.2//EN"|
                     . q| "http://www.wapforum.org/DTD/wml12.dtd">|, 
    
    ## characters encoding
   'encoding'      => 'utf-8', 
    
    ## links reconstruction default options
   'hreftmpl'      => '{FILEPATH}{FILENAME}{$FILETYPE =~ s/s?html?/wml/o; $FILETYPE}', 
   'srctmpl'       => '{FILEPATH}{FILENAME}{$FILETYPE =~ s/gif|png|jpe?g/wbmp/o; $FILETYPE}', 
    
    ## links reconstruction in CGI mode
   'relative-url'  => 1,    ## use relative self path ?
);

my %options = (
   'help'          => 0,    ## show the usage and exit
   'version'       => 0,    ## show the program name and version and exit
    
    ## conversion options
   'ascii'         => 0,    ## convert named entities to US-ASCII
   'collapse'      => 1,    ## collapse white space characters
   'compile'       => 0,    ## compile WML to binary tokenized data
   'ignore-images' => 0,    ## completly ignore image links
   'img-alt-text'  => 1,    ## replace IMG tags with their ALT attribute
   'linearize'     => 1,    ## suppress the tables tags
   'nopre'         => 0,    ## don't use PRE tag
   'numeric-non-ascii' => 0,  ## convert non-ASCII characters to numeric entities
    
    ## links reconstruction options
   'hreftmpl'      => $defaults{hreftmpl}, 
   'srctmpl'       => $defaults{srctmpl}, 

    ## card splitting options
   'split-card'           => 0,      ## slice the document by cards
   'split-deck'           => 1,      ## slice the document by decks
   'max-card-size'        => 1_10000,  ## maximum size of data per card
   'card-split-threshold' =>    50,  ## card split threshold
   #'next-card-label'      => '[&gt;&gt;]',  ## label of the link to go to the next card
   #'prev-card-label'      => '[&lt;&lt;]',  ## label of the link to go to the previous card
   'next-card-label'      => '[下页]',  ## label of the link to go to the next card
   'prev-card-label'      => '[上页]',  ## label of the link to go to the previous card
    
    ## HTTP authentication
   'http-user'     => '',   ## HTTP user
   'http-passwd'   => '',   ## HTTP password
    
    ## proxy support
   'proxy'         => 0,    ## turn proxy support on/off
    
    ## debugging options
   'debug'         => undef,## activate the debug mode
   'xmlcheck'      => 0,    ## perform a well-formedness check (using XML::Parser)
);

# You should not edit below this line unless you know what you are doing.     #
# --------------------------------------------------------------------------- #

# 
# globals
# 
sub debug;
sub warning;
sub fatal;

use vars qw($cgi);
$cgi = 0;
my $agent;   ## LWP user agent
my $result;  ## WML deck in text format
my $binary;  ## WML deck in binary format
my $xmlckres = '';
my $complres = '';

my %optname = (
   'a' => 'ascii', 
   'c' => 'xmlcheck', 
   'd' => 'debug', 
   'i' => 'ignore-images', 
  #'h' => 'help',         ## shell only
   'k' => 'compile', 
   'n' => 'numeric-non-ascii', 
  #'o' => 'output',       ## shell only
   'p' => 'nopre', 
   'P' => 'http-passwd', 
   's' => 'max-card-size', 
   't' => 'card-split-threshold', 
   'U' => 'http-user', 
  #'v' => 'version',      ## shell only
);
my %optchar = ();

## used by the html parser, golbal variables
use vars qw(%state);
%state = (
    doc_uri  => '',        ## document absolute URI
    doc_name => '',        ## document file name
    self_url => '',        ## the CGI's URL for self-referencing
    self_srv => '',        ## the CGI's server
    output   => '',        ## buffer for storing output
    type     => 'wml',     ## type of the output
    decks    => {},        ## hash that contains the decks, indexed by their id
    skip     => 0,         ## skip switch (on/off)
    stack    => [],        ## tag stack
    cardsize => 0,         ## size of the current card/deck
    decksize => 0,         ## size of the current card/deck
    #cardid   => 'wdf000',  ## ID of the current card/deck (stands for "WML Document - Fragment 000")
    cardid   => '1',  ## ID of the current card/deck (stands for "WML Document - Fragment 000")
    title    => '',        ## title of the WML deck
    encoding => '',        ## encoding of the document
    form     => {          ## hash that contains the current form data
        href    => '',     ##  - URL
        method  => '',     ##  - method
        fields  => [],     ##  - fields list
    }, 
);

my %entities = ();  ## named entities conversion table
my %num2ascii = (); ## non-ASCII characters to ASCII equivalent conversion table

# 
# The following two hashes are based on the WML DTD. They are the hardcoded 
# conversion tables which describe the legal syntax of WML tags. 
# 
my %dtdent = ();
    $dtdent{emph}   = 'em,strong,b,i,u,big,small';
    $dtdent{layout} = 'br';
    $dtdent{text}   = $dtdent{emph};
    $dtdent{flow}   = "$dtdent{text},$dtdent{layout},img,anchor,a,table";
    $dtdent{task}   = 'go,prev,refresh,noop';
    $dtdent{fields} = "$dtdent{flow},input,select,fieldset";

my %with = (
    html     => { action => 'replace',  new_value => 'wml' }, 
    wml      => { action => 'keep',     nest => 'head,template,card',  unique => 1 }, 
    
    ## header tags
    head     => { action => 'keep',     nest => 'meta,access',  unique => 1 }, 
   # meta     => { action => 'keep',     nest => 'EMPTY',  attributes => 'http-equiv,name,content,forua,scheme' }, 
    template => { action => 'keep',     nest => 'do,onevent',  unique => 1 }, 
    title    => { action => 'skip' }, 
    base     => { action => 'replace',  new_value => '' }, 
    style    => { action => 'skip' }, 
    script   => { action => 'skip' }, 
    
    ## structural tags
    body     => { action => 'replace',  new_value => 'card' }, 
    card     => { action => 'keep',     nest => 'onevent,timer,do,p,pre',  unique => 1 }, 
    h1       => { action => 'replace',  new_value => 'p',  render => 'big,strong',  special => 'nowidow' }, 
    h2       => { action => 'replace',  new_value => 'p',  render => 'big',  special => 'nowidow'}, 
    h3       => { action => 'replace',  new_value => 'p',  render => 'strong',  special => 'nowidow' }, 
    h4       => { action => 'replace',  new_value => 'p',  special => 'nowidow' }, 
    h5       => { action => 'replace',  new_value => 'p',  special => 'nowidow' }, 
    h6       => { action => 'replace',  new_value => 'p',  special => 'nowidow' }, 
    li       => { action => 'replace',  new_value => 'p' }, 
    dt       => { action => 'replace',  new_value => 'p' }, 
    dd       => { action => 'replace',  new_value => 'p' }, 
    div      => { action => 'replace',  new_value => 'p' }, 
    p        => { action => 'keep',     nest => "$dtdent{fields},do",  attributes => 'align' }, 
    br       => { action => 'keep',     nest => 'EMPTY' }, 
    pre      => { action => 'keep',     nest => 'a,br,i,b,em,strong,input,select' }, 
    tt       => { action => 'replace',  new_value => 'pre' }, 
    
    ## tables tags
    table    => { action => 'keep',     nest => 'tr',  attributes => 'title,align' }, 
    caption  => { action => 'skip' }, 
   'tr'      => { action => 'keep',     nest => 'td' }, 
    th       => { action => 'replace',  new_value => 'td' }, 
    td       => { action => 'keep',     nest => "$dtdent{emph},$dtdent{layout},img,a,anchor" }, 
    
    ## link tags
    a        => { action => 'keep',     nest => 'br,img',  attributes => 'id,name,href,title,accesskey', 
                                        attrconv => { name => 'id' } }, 
    anchor   => { action => 'keep',     nest => 'br,go,img',  attributes => 'id,title,accesskey' }, 
    img      => { action => 'keep',     nest => 'EMPTY',  attributes => 'id,src,alt,align' }, 
    frame    => { action => 'replace',  new_value => 'p' }, 
    area     => { action => 'replace',  new_value => 'p' }, 
    
    ## style tags
    em       => { action => 'keep',     nest => $dtdent{flow} }, 
    strong   => { action => 'keep',     nest => $dtdent{flow} }, 
    b        => { action => 'keep',     nest => $dtdent{flow} }, 
    i        => { action => 'keep',     nest => $dtdent{flow} }, 
    u        => { action => 'keep',     nest => $dtdent{flow} }, 
    big      => { action => 'keep',     nest => $dtdent{flow} }, 
    small    => { action => 'keep',     nest => $dtdent{flow} }, 
    
    ## events
   'do'      => { action => 'keep',     nest => $dtdent{task},  attributes => 'type,label,name,optional' }, 
    onevent  => { action => 'keep',     nest => $dtdent{task},  attributes => 'type' }, 
    
    ## tasks
   'go'      => { action => 'keep',     nest => 'postfield,setvar',  attributes => 'href,method,enctype,sendreferer,cache-control,accept-charset' }, 
    postfield=> { action => 'keep',     nest => 'EMPTY',  attributes => 'name,value' }, 
    setvar   => { action => 'keep',     nest => 'EMPTY',  attributes => 'name,value' }, 
    prev     => { action => 'keep',     nest => 'setvar' }, 
    refresh  => { action => 'keep',     nest => 'setvar' }, 
    noop     => { action => 'keep',     nest => 'EMPTY' }, 
    
    ## form tags
    form     => { action => 'replace',  new_value => '' }, 
   'select'  => { action => 'keep',     nest => 'optgroup,option',  attributes => 'title,name,value,multiple' }, 
    optgroup => { action => 'keep',     nest => 'optgroup,option',  attributes => 'title' }, 
    option   => { action => 'keep',     nest => 'onevent',  attributes => 'title,value' }, 
    input    => { action => 'keep',     nest => 'EMPTY',  attributes => 'name,type,value,title,size,maxlength'}, 
    fieldset => { action => 'keep',     nest => "$dtdent{fields},do",  attributes => 'title' }, 
    timer    => { action => 'keep',     nest => 'EMPTY',  attributes => 'name,value' }, 
);


# 
# The following hash hardcodes the parent-lookup for each element 
# of the WML syntax, i.e. for each element, it gives the prefered 
# parent element. 
# 
my %reverse = (
    ## head tags
    wml => '',          head => 'wml',      meta => 'head',     
    access => 'head',   template => 'wml',  onevent => 'template', 
    
    ## structural tags
    card => 'wml',      p => 'card',        pre => 'card',      br => 'p',
    
    ## tables tags
    table => 'p',      'tr' => 'table',     td => 'tr',
    
    ## link tags
    a => 'p',           anchor => 'p',      img => 'p',
    
    ## style tags
    b => 'p',           i => 'p',           u => 'p', 
    strong => 'p',      em => 'p', 
    big => 'p',         small => 'p', 
    
    ## form tags
   'select' => 'p',     option => 'select', optgroup => 'select', 
   'do' => 'p',         input => 'p',       fieldset => 'p',
);



# 
# main
# 
$| = 1;
my $time1=0;
my $time2=0;
my $time3=0;
my $time4=0;
my $time5=0;
my $l_time1 =0;
my $l_time2 =0;
my $l_time3 =0;
my $l_time4 =0;
my $startime = getMS();

Getopt::Long::Configure(qw(no_auto_abbrev));

fileparse_set_fstype('Unix');  ## this is because I use fileparse() to 
                               ## split the URL fragments

## CGI security options
$CGI::POST_MAX = 1024 * 1;  # max 1K posts
$CGI::DISABLE_UPLOADS = 1;  # no uploads

load_entities();

## create the user agent
$agent = new LWP::UserAgent protocols_forbidden => ['file'];
$agent->agent("[$program/$version ".$agent->agent.']');

for my $opt (keys %optname) {
    $optchar{$optname{$opt}} = $opt
}

## constructing %num2ascii using data from %entities
for my $ent (keys %entities) {
    $num2ascii{$entities{$ent}[0]} = $entities{$ent}[1]
}

if(@ARGV or isatty(\*STDOUT)) {
    ## launched from shell
    
    my @opts = (
      ## usage options
      qw(help|h|H  version|v|V),
      
      ## conversion options
      qw(ascii|a!  collapse!  ignore-images|i  img-alt-text!  
         linearize!  nopre|p  numeric-non-ascii|n), 
      
      ## links reconstructions options
      qw(hreftmpl=s  srctmpl=s), 

      ## card splitting options
      qw(split-card  split-deck
         max-card-size|s=i  card-split-threshold|t=i 
         next-card-label=s  prev-card-label=s), 
      
      ## HTTP authentication
      qw(http-user|U=s  http-passwd|P=s), 
      
      ## proxy support
      qw(proxy|Y!), 
      
      ## output options
      qw(compile|k  output|o=s), 

      ## debugging options
      qw(debug|d:i  xmlcheck|c!)
    );
    
    ## getting options
    GetOptions(\%options, @opts);
    version() if $options{version};
    usage() if $options{help};
    usage() unless @ARGV;
    apply_options();

    ## converting the file
    $result = html2wml(shift);
    
} else {
    ## launched from web
    $cgi = new CGI;
    $agent->agent($cgi->user_agent . ' ' . $agent->agent);
    $cgi->compile(qw(param url header));
    
    ## get the options
    for my $param ($cgi->param) {
        my $option = length($param) == 1 ? $optname{$param} : $param;
        next unless exists $options{$option};
        $options{$option} = $cgi->param($param)
    }
    
    apply_options();
    
    $state{doc_name} = 'output';
    
    ## creating static part of the self url
    my $cgi_options = '';
    for my $param ($cgi->param) {
        next if 'url,id' =~ /\b$param\b/;
        my $value = $cgi->param($param);
        next unless $value;
        next unless exists $options{$param} or exists $options{$optname{$param}};
        my $opt = exists $optchar{$param} ? $optchar{$param} : $param;
        $cgi_options .= "$param=$value;" 
    }
    
    $state{self_url} = $cgi->url(-relative => $defaults{'relative-url'}) . "?$cgi_options";
    
    ## send debug header if needed
    print $cgi->header if $options{'debug'};
    
    $time1 = getMS();    
    ## execute main part
    $result = html2wml($cgi->param('url') || '/');
}

$time2 = getMS();    
## special case: splitting by decks
if($cgi and $options{'split-deck'}) {
    ## return the desired deck (as specified by the id parameter) 
    ## or the first deck if none has been specified
    $result = $state{decks}{ $cgi->param('id') || (sort keys %{$state{decks}})[0] }
}

    $time3 = getMS();    

## XML check
## for debug test, don't check
$options{'xmlcheck'} = 0;
if($options{xmlcheck}) {
    
## for development only :-)
##    $result =~ s{"http://www.wapforum.org/DTD/wml12.dtd"}                           #XXX#
##                {"/Users/madingue/Documents/Softwares/Html2Wml/devel/t/wml12.dtd"}; #XXX#
## ---
    
    eval {
      require XML::Parser;
      my $parser = new XML::Parser Style => 'Tree', ErrorContext => 2;
      $parser->parse($result);
    };
    $@ =~ /Can't locate/ and $@ = '(XML::Parser not available)';
    $xmlckres = $@ ? "\nExpat errors\n$@" : "Expat: well-formed";
    
    eval {
      require XML::LibXML;
      my $parser = new XML::LibXML;
      $parser->validation(1);
      $parser->expand_entities(1);
      $parser->load_ext_dtd(1);
      my $dom = $parser->parse_string($result);
      die "document isn't valid" unless $dom->is_valid;
    };
    $@ =~ /Can't locate/ and $@ = ', (XML::LibXML not available)';
    $xmlckres .= $@ ? "\nGnome-XML errors\n$@" : ", Gnome-XML: valid";
    
    eval {
      require XML::Checker::Parser;
      XML::Checker::Parser::map_uri(
          "-//WAPFORUM//DTD WML 1.2//EN" => "file:///Users/maddingue/Documents/Softwares/Html2Wml/devel/t/wml13.dtd"
      );
      my $parser = new XML::Checker::Parser Style => 'Tree', 
              ErrorContext => 2, ParseParamEnt => 1, #NoLWP => 1, 
              SkipExternalDTD => 1, KeepCDATA => 1;
      $parser->parse($result);
    };
    $@ =~ /Can't locate/ and $@ = ', (XML::Checker not available)';
    $xmlckres .= $@ ? "\nXML-Checker errors\n$@" : ", XML-Checker: valid";

}
$time4 = getMS();

## WML tokenization
## TODO:
if($options{compile}) {
    $binary = '';
    my $buf;
    
    eval {
      require IPC::Open2;
      require IO::Handle;
      my $in  = new IO::Handle;
      my $out = new IO::Handle;
      
      my $pid = IPC::Open2::open2($out, $in, $defaults{wmlc}, '-', '-');
      
      print $in $result;
      close($in);
      $binary = join '', <$out>;
      close($out);
      waitpid($pid, 0);
    };
    
    $complres = $@
}
$time5 = getMS();

if($options{'debug'}) { ## debug output
    my $endtime = getMS();
    my $difftime = $endtime - $startime;
    my @times = times;
    $times[0] += $times[2];  ## total user time
    $times[1] += $times[3];  ## total system time
    $times[2] = $times[0] + $times[1];  ## total time
    
    my $i = 1;
    $result .= "\n";
    $result =~ s/^/@{[sprintf '%3d', $i++]}: /gm;  ## add lines number
    $result = simple_wrap($result);
    
    if($cgi) {
        print qq|<html>\n<head>\n<title>$program -- Debug Mode</title>\n|, 
              qq|<style type="text/css">\n  BODY { background-color: #ffffff}\n|, 
              qq|  .tag { color: #8811BB }\n  .attr { color: #553399 }\n </style>\n|, 
              qq|</head>\n<body>\n<h1>$program -- Debug Mode</h1>\n|, 
              qq|<p>This is the result of the conversion of the document |, 
              qq|<a href="$state{doc_uri}">$state{doc_uri}</a> by $program v$version.</p>\n|, 
              qq|<hr />\n|, 
              htmlize($result), 
              qq|<hr />\n<p>Result of XML check:</p>\n|, 
              htmlize($xmlckres); 
        
        print qq|<hr />\n<p>Result of WML compilation:</p>\n<pre>|, 
              ($complres ? "$complres\n" : hextype($binary)), "</pre>\n" 
              if $options{compile}; 
        
        printf "<hr />\n<p>Time: %.3f wallclock secs (%.2f usr + %.2f sys = %.2f cpu)</p>\n", 
               $difftime, @times[0..2];
        
        #printf "<hr />\n<p>[denny debug]before convert:%d    html2wml:%d     split: %d   xmlcheck:%d</p>\n",
                $time1-$startime,$time2-$time1,$time3-$time2,$time4-$time3;   
        printf "<hr />\n<p>[denny debug]html2wml=%.3f     geturl=%.3f preprocess=%.3f convert=%.3f</p>\n",
                $time2-$time1,$l_time2-$l_time1,$l_time3-$l_time2,$l_time4-$l_time3;   
        print qq|\n</body>\n</html>|
        
    } else {
        my $s = "$program -- Debug Mode\n";
        print $s, '-'x length($s), "\n", 
              $result, "\n", ' -'x5, "\n", 
              $xmlckres, "\n";
        print ' -'x5, "\nCompiled WML\n", ' -'x5, "\n", 
              ($complres ? "$complres\n" : hextype($binary)) 
              if $options{compile};
        print ' -'x5, "\n";
        printf "Time: $difftime wallclock secs (%.2f usr + %.2f sys = %.2f cpu)\n", @times[0..2];
        printf "<hr />\n<p>[denny debug]html2wml=%.3f     geturl=%.3f preprocess=%.3f convert=%.3f</p>\n",
                $time2-$time1,$l_time2-$l_time1,$l_time3-$l_time2,$l_time4-$l_time3;   
    }
    
} else { ## normal output
    my $out = \*STDOUT;
    
    if($options{'output'}) {
        open(OUT, ">$options{output}") or fatal "cannot write to '$options{output}': $!\n";
        $out = \*OUT;
    }
    
    if($options{'compile'}) {
        print $out $cgi->header(
            -type => 'application/vnd.wap.wmlc', 
            -content_length => length $result
        ) if $cgi;
        print $out $binary;
    
    } else {
        print $out $cgi->header(
            -type => "text/vnd.wap.wml; charset=$state{encoding}", 
            -content_length => length $result
        ) if $cgi;
        print $out $result;
    }
}



# 
# apply_options()
# -------------
sub apply_options {
    if($options{'linearize'}) {
        delete @with{qw(table tr td th)};
        $with{'caption'} = { action => 'replace', new_value => 'p', render => 'b' };
        $with{'tr'} = { action => 'replace', new_value => 'p' };
        delete @reverse{qw(table tr td)};
    }
    
    if($options{'ignore-images'}) {
        delete $with{'img'};
    }
    
    if(not defined $options{'debug'}) {
        $options{'debug'} = 0;
    } elsif($options{'debug'} == 0) {
        $options{'debug'} = 1;
    }
    
    if($options{'debug'}) {
        $options{'xmlcheck'} = 1;
    }
    
    if($options{'nopre'}) {
        delete $with{'pre'};
        $with{'pre'} = { action => 'replace', new_value => 'p' };
    }
    
    if($cgi) {
		 #TODO: split-card 
#        $options{'split-card'} = 0;
#        $options{'split-deck'} = 1;
        $options{'split-card'} = 0;
        $options{'split-deck'} = 1;
        
        ## security: don't allow to modify the templates 
        ## when called as a CGI
        $options{'hreftmpl'} = $defaults{'hreftmpl'}; 
        $options{'srctmpl'}  = $defaults{'srctmpl'}; 
    }
    
    ## security: check if the templates contains suspicious code
    ## if the templates have changed
    if($options{hreftmpl} ne $defaults{hreftmpl} or $options{srctmpl} ne $defaults{srctmpl}) {
        my $forbidden = join '|', '[``]', map {"\\b$_\\b"} 
            qw(eval exec system unlink kill fork open sysopen pipe socket);
        
        $options{hreftmpl} = $defaults{hreftmpl} if $options{hreftmpl} =~ /$forbidden/; 
        $options{srctmpl}  = $defaults{hreftmpl} if $options{srctmpl}  =~ /$forbidden/; 
    }
    
    $options{'cardsize-limit'} = $options{'max-card-size'} - $options{'card-split-threshold'};
    
    if($^O eq 'MacOS') {
        $options{'compile'} = 0;
    }
    
    if($options{'compile'}) {
        $options{'prev-card-label'} = '[&#38;lt;&#38lt;]';
    }
    
    ## proxy support
    if($options{'proxy'}) {
        if($defaults{'proxy-server'}) {
            ## use hardcoded settings
            $agent->proxy([qw(http ftp gopher)] => $defaults{'proxy-server'});
            
        } else {
            ## load from environment
            $agent->env_proxy();
        }
    }
}


# 
# html2wml()
# --------
sub html2wml {
    my $url = shift;
    my $file = '';
    my $type = '';
    my $enc  = '';
    my $converter = new HTML::Parser api_version => 3;
    
    return unless $url;
    
    $l_time1 = getMS();
    ## read the file 
    if($url =~ m{https?://}) {  ## absolute uri
        ($file,$type,$enc) = get_url($url)
    
    } 
	elsif(not $cgi) {  ## local file
        $file = read_file($url)
    
    } else {  ## absolute url relative to the server
        ($file,$type,$enc) = get_url( $url = URI::URL->new($url, $cgi->url)->abs )
    }
    $l_time2 = getMS();

    $enc ||= '';
    $enc =~ s/charset=//i;
    url_encode($url);
    $state{doc_uri} = $url;
    ($state{self_srv}) = ($state{self_url} =~ m|^(https?://[\w.-]+(?::\d+)?)/|);
    
    ## strip the DOCTYPE
    $file =~ s/<!DOCTYPE[^>]+>//go;
    
    ## try to get the document charset encoding
    if(not $enc and $file =~ m|meta +http-equiv.+charset=["']?([a-zA-Z0-9_-]+)['"]?|i) {
        $enc = lc $1
    }
    
    $state{encoding} = $enc || $defaults{'encoding'};
    
    $type ||= '';
    
    ## if it's an image, call send_image()
    if(index($type, 'image') >= 0 or $url =~ /\.(?:gif|jpg|png)$/i) {
        @_ = ($file, $url);
        goto &send_image
    }
    
    ## get the document title
    if($file =~ m|<title>([^<]+)</title>|i) {
        $state{title} = $1;
        convert_entities($state{title});
        clean_spaces($state{title});
    }
    
    ## WML header
    $state{skip} = 0;
    $state{output} = join '', q|<?xml version="1.0"|, 
        ($state{encoding} ?  qq| encoding="$state{encoding}"| : ''),
        qq|?>\n$defaults{wmlvers}\n|;
    

    ## affectation of the HTML::Parser handlers
    $converter->unbroken_text(1);
    $converter->handler(start       => \&start_tag,   'tagname, attr');
    $converter->handler(end         => \&end_tag,     'tagname');
    $converter->handler(text        => \&text_tag,    'text, is_cdata');
    $converter->handler(comment     => \&comment_tag, 'tokens');
    #$converter->handler(declaration => \&default_handler, 'text');
    #$converter->handler(process     => \&default_handler, 'text');
    #$converter->handler(default     => \&default_handler, 'text');
    
    $l_time3 = getMS();
    ##TODO: begin the conversion, which use 2/3 of all
    $converter->parse($file);
    $converter->eof;
    
    $l_time4 = getMS();
    ## flush the stack
    while(my $tag = pop @{$state{stack}}) {
        $state{output} .= "</$tag>"
    }
    
    post_conversion_cleanup();
    
    $state{decks}{$state{cardid}} = $state{output};
    
    return $state{output}
}


# 
# post_conversion_cleanup()
# -----------------------
# 
sub post_conversion_cleanup {
    ## convert alone ampersand characters to entities
    $state{output} =~ s/\&\s/\&#38; /go;
    
    ## correct unclosed numeric entities
    $state{output} =~ s/(\&#\d+)([^\d;])/$1;$2/go;
    
    ## convert the named HTML entities to numeric entities
    convert_entities($state{output});
    
    ## convert non-ASCII characters to numeric entities
    if($options{'numeric-non-ascii'}) {
        $state{output} =~ s/([\x80-\xFF])/'&#'.ord($1).';'/eg;
    }
    
    ## escape $ chars
    $state{output} =~ s/\$([^(])/\$\$$1/g;
    
    collapse($state{output}) if $options{'collapse'};
    
    ## set the title of the card
    if(length $state{title}) {
        my $title = $state{title};
        $title =~ s/"/\&#34;/go;
        $title =~ s/\$/\$\$/go;
        $title =~ s/(\&#\d+)([^\d;])/$1;$2/go;
        $state{output} =~ s/<card/<card title="$title"/g;
    }
}


# 
# collapse()
# --------
# Collapse empty spaces and paragraphes from the given parameter
# 
sub collapse{
    $_[0] =~ s/\015\012|\012|\015/\n/go;  ## converts CR/LF to native eol
    $_[0] =~ s|\s+>|>|go;    ## collapse spaces inside tags
    $_[0] =~ s|\s+/>|/>|go;  ## collapse spaces inside empty tags 
    $_[0] =~ s|<(\w+) +|<$1 |g;    ## collapse spaces between tag and attributes
    $_[0] =~ s|<p>\s+|<p>|go;      ## collapse spaces at the begining of a paragraph
    $_[0] =~ s|\s+</p>|</p>|go;    ## collapse spaces at the end of a paragraph
    
    ## collapse empty paragraphs
    $_[0] =~ s|<p[^>]*>\s*</p>||go;
    $_[0] =~ s|<p[^>]*>\s*(?:<br/>)+\s*</p>||go;
    $_[0] =~ s|<p[^>]*>\s*(?:\&nbsp;\s*)+</p>||go;
    $_[0] =~ s|<p[^>]*>\s*(?:\&#32;\s*)+</p>||go;
    $_[0] =~ s|<p[^>]*>\s*(?:\[IMG\]\s*)+</p>||go;
    $_[0] =~ s|<(\w+)>\s*</\1>||go;
    
    ## collapse multiple lines
    $_[0] =~ s/\n+/\n/go;
    $_[0] =~ s/(?: +\n)+/\n/go;
}


# 
# get_url()
# -------
# This function gets and returns the file from the given URI. 
# If called in a array context, returns the file content and the associated 
# MIME type (as given by the server). 
# 
sub get_url {
    my $uri = shift;
    my $quiet = shift || 0;
    
    if($cgi and index($uri, 'file:') == 0) {
        cgi_error(q|For security reasons, the file: scheme is not allowed.|)
    }
    
    ##TODO: request and response which waste time 1/3 of all
    # LWP::Simple is bad.
    #my $content = LWP::Simple::get($uri) or die("unknown url\n"); 
    #return $content;
    my $request = new HTTP::Request GET => $uri;
    my $response = $agent->request($request);
   
    if($response->is_error) {
        if($response->status_line == 401) {
            ## Authorization required
            my($realm) = ($response->header('WWW-Authenticate') =~ /realm=(.+)/);
            my $self = "$state{self_url}url=$state{doc_uri}";
            
            if($options{'http-user'} and $options{'http-passwd'}) {
                $request->www_authenticate($response->header('WWW-Authenticate'));
                $request->authorization_basic($options{'http-user'}, $options{'http-passwd'});
                $response = $agent->request($request);
                
            } else {
                if($cgi) {
                    print $cgi->header(-type => 'text/vnd.wap.wml'), <<"PASSFORM"; exit
<?xml version="1.0"?>
$defaults{wmlvers}
<wml><card title="Authentication">
<p>Please enter your user name and password for $realm. </p>
<p>User: <input name="U" type="text" emptyok="false"/><br/>
Password: <input name="P" type="password" emptyok="false"/></p>
<do type="accept"><go href="$self;U=\$(U);P=\$(P)"/></do>
</card></wml>
PASSFORM
                } else {
                    fatal <<"PASSASK"
website requires authentication

The web site requires you to authenticate in order to process your request. 
Please enter your user name and password for $realm. 
Use the --http-user and --http-passwd options (or their short counterparts 
-U and -P). Check the documentation for more information. 
PASSASK
                }
            }
            
        } else {
            my $err = <<"ERR";
The following error occured while trying to access the following URL 
-- $uri --
Error @{[ $response->status_line ]}
ERR
            if($cgi) {
                if($quiet) {
                    warning "can't fetch file:\n", $err;
                    return '';
                } else {
                    cgi_error($err)
                }
            } else {
                fatal "fetch error\n\n", $err
            }
        }
    }
    
	$state{decksize} = length($response->content);
    return wantarray ? ($response->content, $response->content_type,
        $response->content_encoding) : $response->content;
}


# 
# read_file()
# ---------
# This function reads and returns the file from the local disk. 
# 
sub read_file {
    my $filepath = shift;
    my $quiet = shift || 0;
    
    my $dir = dirname($filepath);
    my $file = basename($filepath);
    chdir($dir) if $dir;
    
    open(FILE, $file) or my $failed = 1;
    
    if($failed) {
        if($quiet) {
            warning("can't read file '$file': $!\n") and return ''
        } else {
            fatal("can't read file '$file': $!\n")
        }
    }
    
    local $/ = undef;
    $file = <FILE>;
    close(FILE);
    return $file
}


# 
# send_image()
# ----------
# This function allow Html2Wml to send WBMP images to the client. 
# Currently, it send an empty hardcoded image, but support for 
# conversion from common formats (GIF, JPEG, PNG) will be added soon. 
# 
sub send_image {
    my $data = shift;
    my $path = shift;
    
    my $pixel = pack 'C*', 0, 0, 1, 1, 0xFF;  ## this is one white pixel
    
    ## TODO: add the code to allow conversion using an external program
    
    print $cgi->header(-type => 'image/wbmp', -content_length => length $pixel), $pixel;
    exit
}


# 
# convert_entities()
# ----------------
# This function converts the named HTML entities into numeric entities. 
# 
sub convert_entities {
    my $ascii = $options{ascii};
    
    ## try to correct unclosed named entities
    $_[0] =~ s/(&\w{2,6})\b([^;])/$1;$2/go;
    
    ## convert numeric entities and non-ASCII characters 
    ## to ASCII equivalent if requested
    if($ascii) {
        $_[0] =~ s/&#(\d+);/$num2ascii{$1}/g;
        $_[0] =~ s/([\x80-\xFF])/$num2ascii{ord($1)}/g;
    }
    
    my $code = q|  while($_[0] =~ /&(\w+);/g) {                   |
             . q|      my $ent = $1;                              |
             . q|      if(exists $entities{$ent}) {               |
    .($ascii ? q|          my $chr = $entities{$ent}[1];          |
             : q|          my $chr = '&#'.$entities{$ent}[0].';'; | )
             . q|          $_[0] =~ s/&$ent;/$chr/g               |
             . q|      }                                          |
             . q|  }                                              |;
    
    eval $code;
    
    if($_[0] =~ /&(\w{2,6});?/) {
        ## there are some residual unknown or incorrect named entities
        while($_[0] =~ /&(\w{2,6});?/g) { 
            my $ent = $1;
            
            ## check if $ent is a known entity
            if(exists $entities{$ent}) {
                warning "unclosed entity: $ent, corrected\n";
                my $chr = $ascii ? $entities{$ent}[1] : '&#'.$entities{$ent}[0].';';
                $_[0] =~ s//$chr/;
                next
            }
            
            my($e1,$e2) = ('','');
            
            ## split the entity in two parts and check if the first part 
            ## is a valid entity name
            ## entities names are between 2 and 6 characters long, so this 
            ## loop won't be executed more than 4 times
            for my $i (2..length($ent)) {
                $e1 = substr($ent, 0, $i);
                $e2 = substr($ent, $i);
                last if exists $entities{$e1}
            }
            
            if(exists $entities{$e1}) {
                warning "unknown entity: $ent, replaced with $e1\n";
                my $chr = $ascii ? $entities{$e1}[1] : '&#'.$entities{$e1}[0].';';
                $_[0] =~ s//$chr$e2/;
            } else {
                warning "unknown entity: $ent\n";
                $_[0] =~ s//&#38;$ent/;
            }
        }
    }
    
    ## escape the remaining ampersands
    $_[0] =~ s/&(\w+[^;])/&#38;$1/g;
}


# 
# clean_spaces()
# ------------
sub clean_spaces {
    $_[0] =~ s/\t+/ /go;
    $_[0] =~ s/^\s+/ /go;
    $_[0] =~ s/ +/ /go;
}


# 
# HTML::Parser start tag handler
# 
sub start_tag {
    my($tag, $attr) = @_;
    local $_;
    return unless exists $with{$tag};
    
    return if $state{skip};
    
    my $curr_tag = ($with{$tag}{action} eq 'replace' ? $with{$tag}{new_value} : $tag);
    my $prev_tag = scalar @{$state{stack}} ? ${$state{stack}}[-1] : 0;
    
    ## prevent incorrect auto-nesting
    return if $curr_tag eq $prev_tag and $with{$curr_tag}{unique} and $with{$curr_tag}{nest} !~ /\b$curr_tag\b/;
    
    ## special case: replacing image with its alternative text when necessary
    if($curr_tag eq 'img' and $options{'img-alt-text'}) {
        my $alt = $attr->{alt} || $attr->{title} || $attr->{id} || $attr->{name} || '[IMG]';
        text_tag($alt) and return
    }
    
    ## special case: <frame> tag
    if($tag eq 'frame') {
        if($prev_tag eq 'p') { pop @{$state{stack}}; $state{output} .= '</p>' }
        if($prev_tag eq 'wml') { push @{$state{stack}}, 'card'; $state{output} .= '<card>' }
        my $link = xlate_url($$attr{src}, 'href');
        $state{output} .= qq|<p><small>Frame: <a href="$link">$$attr{name}</a></small></p>|;
    }
    
    ## special case: <area> image map tag
    if($tag eq 'area') {
        if($prev_tag eq 'p') { pop @{$state{stack}}; $state{output} .= '</p>' }
        if($prev_tag eq 'wml') { push @{$state{stack}}, 'card'; $state{output} .= '<card>' }
        my $link = xlate_url($$attr{href}, 'href');
        $state{output} .= qq|<p><small>Image map: <a href="$link">$$attr{href}</a></small></p>|;
    }
    
    ## special case: when inside a <a> don't allow opening tags
    if($prev_tag eq 'a' and $with{a}{nest} !~ /\b$curr_tag\b/) {
        return
    }
    
    ## special case: <a name=".."> is replaced by <anchor id="..">
    if($curr_tag eq 'a' and not exists $attr->{href}) {
        $curr_tag = $tag = 'anchor';
        $attr->{id} = exists $attr->{id} ? $attr->{id} : $attr->{name};
        delete $attr->{name};
    }
    
    ## special case: <base> element that defines a base URL
    if($tag eq 'base') {
        $state{doc_uri} = URI::URL->new($attr->{href}, $state{doc_uri})->abs;
    }
    
    ## special case: form declaration
    if($tag eq 'form') {
        $state{form}{href} = xlate_url($attr->{action});
        $state{form}{method} = lc($attr->{method}) || 'get';
        $state{form}{enctype} = $attr->{enctype} || '';
        return;
    }
    
    ## special case: form input
    if($curr_tag eq 'input' and $attr->{type} ne 'submit') {
#        push @{$state{form}{fields}}, $attr->{name};
#        
#        ## special case: hidden form input
#        if($attr->{type} eq 'hidden') {
#            $state{output} .= q|<setvar name="|. $attr->{name} .q|" value="|. $attr->{value} .q|"/>|;
#            return;
#        }
    }
    
    ## special case: form submission
	##TODO: process input, erase, add by denny, 2011-7-20
    if($curr_tag eq 'input' and $attr->{type} eq 'submit') {
        my $method = $state{form}{method};
        
#        $state{output} .= '<do type="accept">';
#        
#        if($method eq 'post') {
#            $state{output} .= qq|<go method="$method" href="$state{form}{href}">|;
#            
#            for my $field (@{$state{form}{fields}}) {
#                $state{output} .= qq|<postfield name="$field" value="\$($field)"/>|;
#            }
#            
#            $state{output} .= '</go>';
#            
#        } else {
#            warning("unknown method '$method'; defaulting to 'get'") if $method ne 'get';
#            
#            my @query = ();
#            for my $field (@{$state{form}{fields}}) {
#                push @query, qq|$field=\$($field)|;
#            }
#            
#            $state{output} .= join '', qq|<go href="$state{form}{href}?|, join('&amp;', @query), '"/>';
#        }
#        
#        $state{output} .= '</do>';
        return;
    }
    
    ## reconstruct well-formed attributes list with only the allowed ones
    if(exists $with{$curr_tag}{attributes} and scalar keys %$attr) {
        my @attrs = ();
        
        for my $param (keys %$attr) {
            if(index($with{$curr_tag}{attributes}, $param) >= 0) {
                $param = $with{$tag}{attrconv}{$param} if exists $with{$tag}{attrconv}{$param};
                my $value = $attr->{$param};
                
                if($param eq 'align' or $param eq 'type') {
                    $value = lc $value
                } elsif($param eq 'href' or $param eq 'src') {
                    $value = xlate_url($value, $param);
                }
                convert_entities($value);
                push @attrs, qq|$param="$value"|;
            }
        }
        
        $attr = join ' ', '', @attrs;
        
    } else {
        $attr = ''
    }
    
    ## set the skip mode state
    $state{skip} = 1 if $with{$curr_tag}{action} eq 'skip';
    
   #debug [2], "\n(start tag) <$tag> => action: ", ($with{$tag}{action} ? $with{$tag}{action} : 'clear'), ($curr_tag ne $tag ? " with $curr_tag " : ''), ($attr? ", attributes:$attr" : ''), "\n";
    
    
    if($with{$curr_tag}{action} eq 'keep') { 
        # TODO: this part of the syntax repairing engine will have to be 
        #       re-written. Maybe a loop on the stack to check whether the 
        #       tree is correct, and in case not, insert the missing ones 
        
        if(scalar @{$state{stack}}) { 
           #debug [2], "  -> syntax repair: closing tags ";
            ## syntax repair: close the tags that were left opened
            while($prev_tag = pop @{$state{stack}}) {
                if($with{$prev_tag}{nest} =~ /\b$curr_tag\b/ 
                or $with{$prev_tag}{nest} =~ /\b$reverse{$curr_tag}\b/) {
                    push @{$state{stack}}, $prev_tag;
                    last
                }
               #debug [2], "</$prev_tag> ";
                $state{output} .= "</$prev_tag>";
            }
           #debug [2], "\n";
        }
    
        ## syntax repair: open the tags that should have been opened
        if($with{$prev_tag}{nest} !~ /\b$curr_tag\b/) {
           #debug [2], "  -> syntax repair: opening tags ";
            
            my($inner_tag,$outter_tag) = ($curr_tag,$prev_tag);
            my @nesting_tags = ();
            
            while($reverse{$inner_tag} and $reverse{$inner_tag} ne $outter_tag) {
                $inner_tag = $reverse{$inner_tag};
               #debug [2], "<$inner_tag> ";
                unshift @nesting_tags, $inner_tag;
            }
            
            push @{$state{stack}}, @nesting_tags;
            for my $t (@nesting_tags) { $state{output} .= "<$t>" }
           #debug [2], "\n";
           #debug [2], "       new stack: (@{$state{stack}})\n";
        }
    }
    
    ## clean up a little
    collapse($state{output}) if $options{'collapse'};
    
    ## split the card if needed
    if($state{cardsize} > $options{'cardsize-limit'} 
      and exists $with{$tag}{special} and $with{$tag}{special} =~ /nowidow/) {
        split_card()
    }
    
    ## simple tag translation
    if($with{$curr_tag}{action} eq 'keep') {
        if($with{$curr_tag}{nest} eq 'EMPTY') {
            $state{cardsize} += length($curr_tag) + length($attr);
            $state{output} .= "<$curr_tag$attr/>"
        } else {
            $state{cardsize} += length($curr_tag) + length($attr);
            $state{output} .= "<$curr_tag$attr>";
            push @{$state{stack}}, $curr_tag;
        }
    
    } else {
        ## do nothing
    }
    
    ## additional rendering effects
    if(defined $with{$tag}{render}) {  ## note that it's $tag, not $curr_tag
        for my $t (split ',', $with{$tag}{render}) {
            $state{cardsize} += length $t;
            $state{output} .= "<$t>"
        }
    }
}


# 
# HTML::Parser end tag handler
# 
sub end_tag {
    my($tag) = @_;
    return unless exists $with{$tag};
    my $curr_tag = ($with{$tag}{action} eq 'replace' ? $with{$tag}{new_value} : $tag);
    
    ## special case: anchors
    if($tag eq 'a' and ${$state{stack}}[-1] eq 'anchor') { $curr_tag = $tag = 'anchor'}
    
    ## special case: form
    if($tag eq 'form') { return }
    
   #debug [2], "( end tag ) </$curr_tag>  stack = (@{$state{stack}})\n\n";
    
    $state{skip} = 0 if $with{$tag}{action} eq 'skip';
    return if $state{skip};
    return if exists $with{$tag}{nest} and $with{$tag}{nest} eq 'EMPTY';
    
    ## additional rendering effects
    if(defined $with{$tag}{render}) {  ## note that it's $tag, not $curr_tag
        for my $t (reverse split ',', $with{$tag}{render}) {
            $state{cardsize} += length $t;
            $state{output} .= "</$t>"
        }
    }
    
    ## special case: /card cleans up the stack
	##TODO:
    if($curr_tag eq 'card') {
        while(${$state{stack}}[-1] ne $curr_tag) {
            my $t = pop @{$state{stack}};
            $state{cardsize} += length $t;
            $state{output} .= "</$t>";
        }
        
        my $s = qq|\n<p align="right"><do type="prev" | . 
            qq|label="$options{'prev-card-label'}"><prev/></do></p>|;
        $state{cardsize} += length $s ;#- 25;
        $state{output} .= $s;
    }
    
    ## closing element
    if(${$state{stack}}[-1] eq $curr_tag  and  $with{$curr_tag}{action} eq 'keep') {
        $state{cardsize} += length $curr_tag;
        $state{output} .= "</$curr_tag> ";
        pop @{$state{stack}};
    
    } else {
        ## do nothing
    }
    
    ## clean up a little
    collapse($state{output}) if $options{'collapse'};
    
    ## check current card size
    if($curr_tag ne 'card' and $curr_tag ne 'wml' and $state{cardsize} > $options{'cardsize-limit'}) {
        split_card()
    }
}


# 
# HTML::Parser text handler
# 
sub text_tag {
    my($text) = @_;
    my $curr_tag = ${$state{stack}}[-1] || '';
    
   #debug [3], "(text node) stack = (@{$state{stack}})\n- - - - -\n$text\n- - - - -\n";
    
    return if $state{skip};
    
    return if $text =~ /^\s*$/s;  ## skip empty lines
    
    ## add a para tag if we're on the card node
    if($curr_tag eq 'card') {
        $state{cardsize} += 4;
        $state{output} .= "\n<p>";
        push @{$state{stack}}, 'p';
    }
    
    clean_spaces($text) if $options{'collapse'} and $curr_tag ne 'pre';
    # 
    # TODO: add the code that split too long chunks of text
    # 
    $state{output} .= $text;
    $state{cardsize} += length $text;
}


# 
# HTML::Parser comment tag handler
# 
sub comment_tag {
    my($comment) = @_;
    local $_;
    
    $comment = join '', @$comment;
    
   #debug [3], "( comment ) stack = (@{$state{stack}})\n    $comment\n";
    
    ## Actions engine
    if($comment =~ /^\s*\[(\w+)\s*(.*)\]\s*$/) {
        my $action = $1;
        my %attributes = map { /\G(\w+)=["']([^"']+)["']/g } split /\s+/, $2;
        
        for my $attr (keys %attributes) {
            if($attr eq 'for') {
                return if $attributes{$attr} ne $state{type};
            }
            if($attr eq 'virtual' and $attributes{virtual} !~ /^http:/) {
                $attributes{virtual} = URI::URL->new( $attributes{virtual}, $state{doc_uri} )->abs
            }
        }
        
        for($action) {
            /include/ and do {
                my $buf;
                if($attributes{virtual}) {
                    $buf = get_url($attributes{virtual}, 1);
                } elsif($attributes{file}) {
                    $buf = read_file($attributes{file}, 1)
                }
                $state{output} .= $buf;
                $state{cardsize} = length $buf;
            };
            
            /skip/ and do {
                $state{skip} = 1;
            };
            
            /end_skip/ and do {
                $state{skip} = 0;
            };
            
            /fsize/ and do {
                my $buf;
                if($attributes{virtual}) {
                    $buf = length get_url($attributes{virtual}, 1);
                } elsif($attributes{file}) {
                    $buf = length read_file($attributes{file}, 1)
                }
                $state{output} .= $buf;
                $state{cardsize} = length $buf;
            };
        }
    }
}


# 
# HTML::Parser default handler
# 
sub default_handler {
    my($text) = @_;
   #debug [2], "( default ) [$text]\n\n";
}


# 
# split_card()
# ----------
# This function closes the current card and creates a new one. 
# 
sub split_card {
    my @stack = @{$state{stack}};
    shift @stack;  ## shift the <wml> tag
    shift @stack;  ## shift the <card> tag
    
	#TODO: footer, add by denny,
	##my $cardnum = $state{cardsize}/$options{'cardsize-limit'};
	my $cardnum = int($state{decksize}/$options{'max-card-size'});
    my $id = $state{cardid};
    my $preid = ($state{cardid} <= 1) ? 1 : ($state{cardid}-1);
    my $nextid = ($state{cardid} >= $cardnum) ? $cardnum : ($state{cardid}+1);
	$state{cardid}++;
    $state{cardsize} = 0;
    #debug [2], "(splitcard) stack = (@{$state{stack}})\n\n";
    
    for my $tag (reverse @stack) { $state{output} .= "</$tag>" }
    
    my $doc_uri = $state{doc_uri};
    
    # strip the server part if the document and this CGI are on the same server
    $doc_uri =~ s/^$state{self_srv}//o if $cgi;
    
    my $link_to_preq = $options{'split-deck'} ?
        "$state{self_url}url=$doc_uri&id=$preid" : "#$preid";
	my $link_to_next = $options{'split-deck'} ?
		"$state{self_url}url=$doc_uri&id=$nextid" : "#$nextid";
   
	#TODO: output footer, add by denny,  output next
#    $state{output} .= join '', qq|<br />-------------<br /><p align="left">|, 
#        qq|<do type="prev" label="$options{'prev-card-label'}"><prev/></do>|, 
#        qq|<do type="accept" label="$options{'next-card-label'}"><go href="$link_to_next"/></do>|, 
#        qq|</p>\n</card>\n|;
#<a onclick="return nsWMLcheckLink(this);" href="show.m?pn=2&sr=http%253A%252F%252Fwww.163.com&a=0&q=&esid=BEVaHqLQgtV&wver=s">下页</a>
    $state{output} .= join '', qq|<br />-------------<br />|, 
		qq|<a onclick="return nsWMLcheckLink(this);" href="$link_to_preq">上页 </a>|,
		qq|<a onclick="return nsWMLcheckLink(this);" href="$link_to_next">下页 </a>|,
		qq|第$id/$cardnum<br />|,
		qq|\n</card>\n|;
    
    if($options{'split-deck'}) {
        post_conversion_cleanup();
        $state{output} .= '</wml>';
        $state{decks}{$id} = $state{output};
        $state{output} = join '', q|<?xml version="1.0"|, 
            ($state{encoding} ?  qq| encoding="$state{encoding}"| : ''), 
            qq|?>\n$defaults{wmlvers}\n<wml>|; 
    }

    $state{output} .= qq|<card id="$state{cardid}">\n|;
    
    for my $tag (@stack) { $state{output} .= "<$tag>" }
}


# 
# xlate_url()
# ---------
# This function translates the given url so that the pointed document will 
# pass through this CGI for conversion when in CGI mode, or construct a url 
# that fits the needs of the webmaster using the given template, if present. 
# 
sub xlate_url {
    my $url  = shift;  ## $url is the url from a href or a src attribute
    my $type = shift;  ## $type is 'src' or 'href'
    
    ## URL encode special characters
    url_encode($url);
    
    ## we only treat http URLs
    return $url if $url =~ /^(\w+):/ and index($1, 'http') != 0;
    
    if($cgi) {
        ## CGI mode

        # create the absolute URL relative to the document
        my $link = URI::URL->new($url, $state{doc_uri})->abs;
        
        # strip the server part if the URL and this CGI are on the same server
        $link =~ s/^$state{self_srv}//o;
        
        return "$state{self_url}url=$link"
        
    } else {
        ## shell mode
        
        ## we don't touch URLs other than http(s):
        return $url if $url =~ m|^(\w+):| and index($1, 'http') < 0;
        
        ## This is where the link reconstruction engine lives...  (waah... :)
        
        if($options{"${type}tmpl"} and $url !~ m|^https?://|) { 
            ## we don't touch absolute urls
            
            my $tmpl = $options{"${type}tmpl"};
            my $uri = new URI $url, 'http';
            
            if($uri->path) {
                my($filename,$filepath,$filetype) = fileparse($uri->path, '((?:\.\w+)+)');
                
                my $init_vars = qq|{
                    sub FILEPATH { q<$filepath> }
                    sub FILENAME { q<$filename> }
                    sub FILETYPE { q<$filetype> }
                    sub URL { q<$url> }
                }|;
                
                my $new_url = new Text::Template TYPE => 'STRING', SOURCE => $init_vars.$tmpl
                    or fatal("can't construct template: $Text::Template::ERROR\n"); 
                
                return $new_url->fill_in(HASH => {
                    'FILEPATH' => $filepath,  
                    'FILENAME' => $filename, 
                    'FILETYPE' => $filetype, 
                    'URL' => $url
                }) or fatal("$Text::Template::ERROR\n")
                
            } else {
                return $url
            }
            
        } else {
            return $url
        }
    }
}


# 
# url_encode()
# 
sub url_encode {
    $_[0] =~ s'[$]'%24'go;
    $_[0] =~ s'&'%26'go;
    $_[0] =~ s';'%3b'go;
    $_[0] =~ s'='%3d'go;
    $_[0] =~ s'[?]'%3f'go;
}


# 
# htmlize()
# -------
# This function translate the given text into HTML
# 
sub htmlize {
    my $str = shift;
    
    ## convert special chars to entities
    $str =~ s/&/\&amp;/go;
    $str =~ s/</\&lt;/go;
    $str =~ s/>/\&gt;/go;
    
    ## add a small syntax highlighting
    $str =~ s{(\&lt;[!?/]?)(\w+)(.*?)([!?/]?\&gt;)}
             {<b>$1<span class="tag">$2</span></b><span class="attr">$3</span><b>$4</b>}gs;
    $str =~ s{\&lt;!--(.*?)--\&gt;}{\&lt;!--<i>$1</i>--\&gt;}gs;
    $str =~ s{href="([^\"]+)"}{href="<a href="$1">$1</a>"}gs;
    
    return "<pre>$str</pre>"
}


# 
# hextype()
# -------
# This function generates a human readable representation of binary data
# 
sub hextype {
    my $data = shift;            ## data to print
    my $colwidth = shift || 16;  ## width of ASCII column
    
    my $half = $colwidth/2;
    my $line = 1;
    my $out = '';
    
    while(length $data) {
        my @hex = unpack 'C'x$colwidth, substr($data, 0, $colwidth);
        substr($data, 0, $colwidth) = '';
        $out .= sprintf '%3d:  '. ((('%02x 'x$half).' ')x2) .'   ', $line++, @hex;
        $out .= sprintf ''.('%s'x$half)x2 . "\n", map { $_ > 32 ? chr : '.' } @hex; 
    }
    
    return $out
}


# 
# simple_wrap()
# -----------
# This function wraps the text given in parameter. 
# 
sub simple_wrap {
    my $orig = ref $_[0] ? $_[0] : \$_[0];
    my $text = '';
    my $curlen = 0;
    my $beg = ' 'x5;
    my $cols = 75;
    
    while($$orig =~ m/(\s*\S+\s+)/gm) {
        if($curlen + length($1) > $cols) {
            $text .= "\n$beg$1";
            $curlen = 1 + length($beg) + length($1)
        } else {
            $text .= $1;
            $curlen += length $1;
        }
        $curlen = 0 if index($1, "\n") >= 0;
    }
    
    return $text
}


# 
# load_entities()
# -------------
# 
sub load_entities {
    %entities = (
        ## Special entities
        quot     => [ 34, '&#34;'],## double quote
        quote    => [ 34, '&#34;'],## double quote
        amp      => [ 38, '&#38;'],## ampersand
        apos     => [ 39, '&#39;'],## single quote
        lt       => [ 60, '&#60;'],## less than sign
        gt       => [ 62, '&#62;'],## greater than sign
        
        ## Spacing characters
        nbsp     => [ 32, ' '],    ## non-breaking space (real value #160)
        ensp     => [ 32, ' '],    ## en space (real value: #8194, U+2002)
        emsp     => [ 32, ' '],    ## em space (real value: #8195, U+2003)
        thinsp   => [ 32, ' '],    ## thin space (real value: #8201, U+2009)
        zwnj     => [  0, '' ],    ## zero width non-joiner (real value: #8204, U+200C)
        zwj      => [  0, '' ],    ## zero width joiner (real value: #8205, U+200D)
        
        ## Latin Extended-A entities + Mathematical symbols
        sbquo    => [130, ','],    ## single low-9 quotation mark
        fnof     => [131, 'f'],    ## latin small f with hook = florin
        bdquo    => [132, ',,'],   ## double low-9 quotation mark
        hellip   => [133, '...'],  ## horizontal ellipsis
        dagger   => [134, ' '],    ## dagger
        Dagger   => [135, ' '],    ## double dagger
        circ     => [136, '^'],    ## modifier letter circumflex accent
        permil   => [137, 'o/oo'], ## per mille sign
        Scaron   => [138, 'S'],    ## latin capital letter S with caron
        lsaquo   => [139, '&#60;'],## single left-pointing angle quotation mark
        OElig    => [140, 'OE'],   ## latin capital ligature OE
        lsquo    => [145, "'"],    ## left single quotation mark
        rsquo    => [146, "'"],    ## right single quotation mark
        ldquo    => [147, '"'],    ## left double quotation mark
        rdquo    => [148, '"'],    ## right double quotation mark
        bull     => [149, 'o'],    ## bullet
        ndash    => [150, '-'],    ## en dash
        mdash    => [151, '--'],   ## em dash
        tilde    => [152, '~'],    ## small tilde
        trade    => [153, '(tm)'], ## trademark sign
        scaron   => [154, 's'],    ## latin small letter s with caron
        rsaquo   => [155, '&#62;'],## single right-pointing angle quotation mark
        oelig    => [156, 'oe'],   ## latin small ligature oe
        Yuml     => [159, 'Y'],    ## latin capital letter Y with diaeresis
        
        ## ISO-Latin-1 entities
        iexcl    => [161, '!'], 
        cent     => [162, '-c-'], 
        pound    => [163, '-L-'], 
        curren   => [164, 'CUR'], 
        yen      => [165, 'YEN'], 
        brvbar   => [166, '|'], 
        sect     => [167, 'S:'], 
        uml      => [168, '"'], 
        copy     => [169, '(c)'], 
        ordf     => [170, '-a'], 
        laquo    => [171, '&#60;&#60;'], 
       'not'     => [172, 'NOT'], 
        shy      => [173, '-'], 
        reg      => [174, '(R)'], 
        macr     => [175, '-'], 
        deg      => [176, 'DEG'], 
        plusmn   => [177, '+/-'], 
        sup2     => [178, '^2'], 
        sup3     => [179, '^3'], 
        acute    => [180, "'"], 
        micro    => [181, 'u'], 
        para     => [182, 'P:'], 
        middot   => [183, '.'], 
        cedil    => [184, ','], 
        sup1     => [185, '^1'], 
        ordm     => [186, '-o'], 
        raquo    => [187, '&#62;&#62;'], 
        frac14   => [188, ' 1/4'], 
        frac12   => [189, ' 1/2'], 
        frac34   => [190, ' 3/4'], 
        iquest   => [191, '?'], 
        Agrave   => [192, 'A'], 
        Aacute   => [193, 'A'], 
        Acirc    => [194, 'A'], 
        Atilde   => [195, 'A'], 
        Auml     => [196, 'Ae'], 
        Aring    => [197, 'A'], 
        AElig    => [198, 'AE'], 
        Ccedil   => [199, 'C'], 
        Egrave   => [200, 'E'], 
        Eacute   => [201, 'E'], 
        Ecirc    => [202, 'E'], 
        Euml     => [203, 'E'], 
        Igrave   => [204, 'I'], 
        Iacute   => [205, 'I'], 
        Icirc    => [206, 'I'], 
        Iuml     => [207, 'I'], 
        ETH      => [208, 'DH'], 
        Ntilde   => [209, 'N'], 
        Ograve   => [210, 'O'], 
        Oacute   => [211, 'O'], 
        Ocirc    => [212, 'O'], 
        Otilde   => [213, 'O'], 
        Ouml     => [214, 'Oe'], 
       'times'   => [215, '*'], 
        Oslash   => [216, 'O'], 
        Ugrave   => [217, 'U'], 
        Uacute   => [218, 'U'], 
        Ucirc    => [219, 'U'], 
        Uuml     => [220, 'Ue'], 
        Yacute   => [221, 'Y'], 
        THORN    => [222, 'P'], 
        szlig    => [223, 'ss'], 
        agrave   => [224, 'a'], 
        aacute   => [225, 'a'], 
        acirc    => [226, 'a'], 
        atilde   => [227, 'a'], 
        auml     => [228, 'ae'], 
        aring    => [229, 'a'], 
        aelig    => [230, 'ae'], 
        ccedil   => [231, 'c'], 
        egrave   => [232, 'e'], 
        eacute   => [233, 'e'], 
        ecirc    => [234, 'e'], 
        euml     => [235, 'e'], 
        igrave   => [236, 'i'], 
        iacute   => [237, 'i'], 
        icirc    => [238, 'i'], 
        iuml     => [239, 'i'], 
        eth      => [240, 'e'], 
        ntilde   => [241, 'n'], 
        ograve   => [242, 'o'], 
        oacute   => [243, 'o'], 
        ocirc    => [244, 'o'], 
        otilde   => [245, 'o'], 
        ouml     => [246, 'o'], 
        divide   => [247, '/'], 
        oslash   => [248, 'o'], 
        ugrave   => [249, 'u'], 
        uacute   => [250, 'u'], 
        ucirc    => [251, 'u'], 
        uuml     => [252, 'u'], 
        yacute   => [253, 'y'], 
        thorn    => [254, 'p'], 
        yuml     => [255, 'y'], 
    );
}


# 
# warning()
# -------
sub warning {
    print STDERR 'html2wml: warning: ', @_
}


# 
# fatal()
# -----
sub fatal {
    print STDERR 'html2wml: fatal: ', @_;
    exit -1;
}


# 
# debug()
# -----
sub debug {
    if($options{'debug'}) {
        my $level = ref $_[0] ? shift->[0] : 1;
        print STDERR @_ if $level <= $options{'debug'}
    }
}


# 
# version()
# -------
sub version {
    print "$program/$version\n"; exit
}


# 
# usage()
# -----
sub usage {
    print STDERR <<"USAGE"; exit
usage: $0 [options] file [-o output]

options: 
  -a, --ascii               use 7 bits ASCII emulation to convert named entities
      --nocollapse          don't collapse spaces and empty paragraphs
      --hreftmpl=template   set the template for the links reconstruction engine
  -i, --ignore-images       completly ignore image links
      --noimg-alt-text      don't replace the images by their alternative text
      --nolinearize         don't linearize the tables
  -n, --numeric-non-ascii   convert non-ASCII characters to numeric entities
  -p, --nopre               don't use the <pre> tag
  
      --split-card                  slice the document by cards (default)
      --split-deck                  slice the document by decks
  -s, --max-card-size=size          set the card size upper limit
  -t, --card-split-threshold=size   set the card splitting threshold 
      --next-card-label=label       set the label of the link to the next card
      --prev-card-label=label       set the label of the link to the previous card

  -U, --http-user           set the HTTP user
  -P, --http-passwd         set the HTTP password
  
  -Y, --proxy               use proxy settings provided by environnement
      --noproxy             don't use proxy
  
  -k, --compile             compile the result in binary form
  -o, --output=outfile      select the outpout (stdout if none specified)
   
  -d, --debug=n     activate the debug mode (always prints to stdout)
  -c, --xmlcheck    activate the XML well-formedness and validity check
  
  -h, --help        show this help screen and exit
  -v, --version     show the program name and version and exit

Read the documentation for more information. 
USAGE
}


# 
# cgi_error()
# ---------
sub cgi_error {
    if($options{'debug'}) {
        print <<"OUTPUT"; exit
<html>
<head>
<title>Html2Wml - Error</title>
</head>
<body>
<h1>Html2Wml - Error</h1>
<p>This program was called with incorrect parameters or an error occured 
when processing the request. Please check your request and try again. </p>
<p>@_</p>
<hr />
<p>$program v$version</p>
</body>
</html>
OUTPUT
    } else {
        print $cgi->header(-type => 'text/vnd.wap.wml'), <<"OUTPUT"; exit
<?xml version="1.0"?>
$defaults{wmlvers}
<wml><card title="Html2Wml - Error">
<p>This program was called with incorrect parameters or an error occured 
when processing the request. Please check your request and try again. </p>
<p>@_</p>
<p>_____<br/>$program v$version</p>
</card></wml>
OUTPUT
    }
}

# 
# getms
# ---------
sub getMS{
# use Time::HiRes qw(gettimeofday);
    my @curtime = gettimeofday;
    return ($curtime[0] + $curtime[1]/1000000);    
    #($start_sec, $start_usec) = gettimeofday;
    #return $start_sec*1000 + $start_usec/1000  
}

#1;
