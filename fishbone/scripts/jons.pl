use Win32;
use Win32::IE::Mechanize;

$website="http://members.founderdating.com/profile/1035/grace-lanni";

$website = $ARGV[0];

my $ie = Win32::IE::Mechanize->new( visible => 1, quiet => 1 );

#$ie->get("http://members.founderdating.com/user/signin");
#sleep(10);
# Store next website


$file=$website;
# $file=~s/(.*)(profile.*)/$2\.txt/;
$file=~s/\:/__/g;
$file=~s/\//--/g;
#JC add html so easy to open (april 26, 2013)
$file=~s/\./_/g;
$file="$file.html";

print "2Outputing $website to $file";

$ie->get($website);

$content = $ie->content;
open FILE, ">$file" or die $!;
print FILE $content;
close FILE;



#$ie->submit_form(
#    form_name => 'f',
#    fields    => { username => "jon.clement\@panamantis.com" },
#    button    => { name  => 'btnI' },
#);
