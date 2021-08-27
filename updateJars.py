# AOTX
# SDS Modernization & Migration - Silver Lining team
# Created by df828t on 8/3/2021
# Purpose of this script to support the build process for AOTX.
# For all the files, we place them in the appropriate place on the root directory on the Azure VM for that region
# There are two 'MECE' processes for this for all the files
# Process 1:
# This is only for JAR files and the WAR file. Since its just a few files (some with multiple locations on app vm),
#  ... we can just pull from that specific git dir containing the jars
# TODO: Implement Process 2
# Process 2 is for all other types of files:
# Based on the git diff we parse through on the app VM, we'll grab a list of files that have changed / been added.
# The script will use the relative src path to copy updated / new files to the same src dst under the root directory.

import os
import shutil

#TODO: Update these global vars based on App VM, not local testcase
LOCAL_GIT_DIR_PATH = '/test/aotx_azure'
LOCAL_GIT_JAR_DIR_PATH = LOCAL_GIT_DIR_PATH + '/site_specific/jars' #also contains .war
ROOT_DIR = '/opt/app/p1c1w141'
VERBOSE = True
DRYRUN = True


def findPathsToJar(filename, rootdir='.'):
    # print(f'Grabbing all filepaths for {filename}')  # Press Ctrl+F8 to toggle the breakpoint.
    # len_git_dir_path = len(LOCAL_GIT_DIR_PATH)
    locations = []
    for subdir, dirs, files in os.walk(rootdir):
        for file in files:
            bname = os.path.basename(file)
            if bname == filename:
                # TODO: remove the dirs used in CodeCloud but are not on server
                fullpath = os.path.join(subdir, file)
                locations.append(fullpath)

    return locations


def findPathsToAllJars(filenames, rootdir='.'):
    '''
    :param filenames: a list of jar filename strings. i.e. ['aotxweb.jar', 'xyz.war, 'cic.jar']
    :param rootdir: a string of the directory path to recursively search through
    :return: a dictionary mapping the basefilename to a list of all the filepaths discovered in the rootdir.
    '''

    len_git_dir_path = len(LOCAL_GIT_DIR_PATH)
    relevant_filepaths = {}
    for fname in filenames:
        list_of_paths_to_fname = findPathsToJar(fname, rootdir=rootdir)
        relevant_paths_to_fname = []
        # TODO: Verify if we should ignore gitrepo dir when making replacements
        # Filtering out gitrepo dir b/c irrelevant to update these
        for apath in list_of_paths_to_fname:
            if apath[0:len_git_dir_path] != LOCAL_GIT_DIR_PATH:
                relevant_paths_to_fname.append(apath)
        relevant_filepaths[fname] = relevant_paths_to_fname

    return relevant_filepaths

def replaceOldJARs(source_filepaths, rootdir='.', verbose=False, dryrun=False):
    filenames = []
    for fpath in source_filepaths:
        filenames.append(os.path.basename(fpath))
    destination_filepaths = findPathsToAllJars(filenames, rootdir=rootdir)
    for fname, fpath in zip(filenames, source_filepaths):
        src = fpath
        dest_fpaths = destination_filepaths[fname]
        for dst in dest_fpaths:
            if verbose:
                print('src: {} | dst: {}'.format(src, dst))
            if dryrun is False:
                newPath = shutil.copy(src, dst, follow_symlinks=False)

    if verbose:
        print("Successfully updated JARs")

    return filenames, destination_filepaths

def getJarFilesFullSrcPaths(gitrepo_dir):
    jar_files_source_paths = []
    for apath in os.listdir(gitrepo_dir):
        full_file_source_path = os.path.join(gitrepo_dir, apath)
        jar_files_source_paths.append(full_file_source_path)
    return jar_files_source_paths



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    jar_files_src_paths = getJarFilesFullSrcPaths(LOCAL_GIT_JAR_DIR_PATH)
    # Setting verbose = True will print each pair of source and destination locations involved with the JAR updates
    # Setting dryrun = True will do everything the same except the final step of actually copying the files over
    jar_filenames, jar_dst_filepaths = replaceOldJARs(jar_files_src_paths, verbose=VERBOSE, dryrun=DRYRUN)
