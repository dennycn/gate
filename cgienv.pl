#! /bin/perl -wT

use strict;

print "Content-type: text/html\n\n";

my $var_name;
foreach $var_name ( sort keys %ENV ){
    print "<P><B>$var_name<</B></P>";
    print $ENV($var_name);
}
