<?php
require "/Users/jvkersch/projects/sat/composer/src/bootstrap.php";

use Composer\DependencyResolver\Decisions;
use Composer\DependencyResolver\DefaultPolicy;
use Composer\DependencyResolver\Pool;
use Composer\DependencyResolver\Request;
use Composer\DependencyResolver\RuleWatchGraph;
use Composer\DependencyResolver\RuleWatchNode;
use Composer\DependencyResolver\Solver;
use Composer\DependencyResolver\Transaction;
use Composer\Json\JsonFile;
use Composer\Package\CompletePackage;
use Composer\Package\Link;
use Composer\Package\LinkConstraint\MultiConstraint;
use Composer\Package\LinkConstraint\VersionConstraint;
use Composer\Package\Loader\ArrayLoader;
use Composer\Repository\ArrayRepository;
use Composer\Repository\FilesystemRepository;
use Composer\Repository\InstalledFilesystemRepository;
use Composer\Repository\PackageRepository;
use Composer\Repository\WritableArrayRepository;

$loader = new ArrayLoader();

/* Remote repository definition */
$json_string = file_get_contents("remote.json");
$packages = JsonFile::parseJson($json_string);

$remote_repo = new ArrayRepository();
foreach ($packages as $packageData) {
    $package = $loader->load($packageData);
    $remote_repo->addPackage($package);
}

/* Installed repository definition */
$json_string = file_get_contents("installed.json");
$packages = JsonFile::parseJson($json_string);

$installed_repo = new ArrayRepository();
foreach ($packages as $packageData) {
    $package = $loader->load($packageData);
    $installed_repo->addPackage($package);
}

/* Pool definition */
$pool = new Pool();
$pool->addRepository($remote_repo);
$pool->addRepository($installed_repo);


$request = new Request($pool);
$request->install("numpy", new MultiConstraint(array()));

class DebuggingSolver extends Solver
{
    public function printRules(Request $request)
    {
        $this->jobs = $request->getJobs();

        $this->setupInstalledMap();

        $this->decisions = new Decisions($this->pool);

        $this->rules = $this->ruleSetGenerator->getRulesFor($this->jobs, $this->installedMap);
        $this->watchGraph = new RuleWatchGraph;

        foreach ($this->rules as $rule) {
            printf("%s\n", $rule);
            // print_r( $rule->getLiterals() );
            
        }
    }
}

$policy = new DefaultPolicy();

$solver = new DebuggingSolver($policy, $pool, $installed_repo);
$solver->printRules($request);
