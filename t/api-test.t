use strict;
use Bio::KBase::Transform::Client;
use Test::More tests => 5;
use Data::Dumper;
use Test::Cmd;
use JSON;


my $ws_id="loader_test";
my $in_id = "Loader.csv-1.0";
my $out_id = "test_pair2";
my $cc = Bio::KBase::Transform::Client->new("http://localhost:7778");

print "This test requires the $in_id is stored in $ws_id(workspace)\n";
print "It also requires read and write ability in the $ws_id(workspace)\n";
ok( defined $cc, "Check if the server is working" );

#my $job_id = $cc->validate({etype => $in_id, id => "d3eecb7f-5b52-4b63-9871-62ecedfd149e"});
my $job_id = $cc->upload({etype => "Transform.CSV", kb_type => "Transform.Pair", in_id => "d3eecb7f-5b52-4b63-9871-62ecedfd149e", "ws_name" => "loader_test", "obj_name" => "api-test-pair"});
ok(ref($job_id) eq "ARRAY","mys_example returns an array");
ok(@{$job_id} eq 2, "returns two job ids for mys_example");

my $job_id = $cc->validate({etype => "Transform.CSV", in_id => "d3eecb7f-5b52-4b63-9871-62ecedfd149e"});
ok(ref($job_id) eq "ARRAY","mys_example returns an array");
ok(@{$job_id} eq 2, "returns two job ids for mys_example");

my $job_id = $cc->validate({etype => "KBaseGenomes.GBK", in_id => "a2a7e05a-35a0-4ac6-8a63-a0ef98796829"});
ok(ref($job_id) eq "ARRAY","mys_example returns an array");
ok(@{$job_id} eq 2, "returns two job ids for mys_example");

my $job_id = $cc->upload({etype => "KBaseGenomes.GBK", kb_type => "KBaseGenomes.ContigSet", in_id => "a2a7e05a-35a0-4ac6-8a63-a0ef98796829", "ws_name" => "loader_test", "obj_name" => "NC005213.cs"});
ok(ref($job_id) eq "ARRAY","mys_example returns an array");
ok(@{$job_id} eq 2, "returns two job ids for mys_example");

my $job_id = $cc->upload({etype => "KBaseGenomes.GBK", kb_type => "KBaseGenomes.Genome", in_id => "a2a7e05a-35a0-4ac6-8a63-a0ef98796829", "ws_name" => "loader_test", "obj_name" => "NC005213.gn", "opt_args" => '{"validator":{},"transformer":{"contigset_ref":"loader_test/NC005213.cs"}}'});
ok(ref($job_id) eq "ARRAY","mys_example returns an array");
ok(@{$job_id} eq 2, "returns two job ids for mys_example");

# TODO: wait job to be done

# TODO: check the internal value to be correct