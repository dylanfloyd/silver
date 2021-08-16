import os
import sys
import git
import re
import shutil
from git import Repo, RemoteProgress
from pprint import pprint
from datetime import datetime
from pathlib import Path

# Reference GitPython module doc here: https://buildmedia.readthedocs.org/media/pdf/gitpython/1.0.2/gitpython.pdf
DRY_RUN = True
ROOT_DIR = './'
GIT_REPO_DIR = 'datadisk/aotx_azure'
COMPILED_JARS_DIR = GIT_REPO_DIR + '/jars'
EWO_JAR_SRC_FILES = GIT_REPO_DIR + '/ewo'
CIC_JAR_SRC_FILES = GIT_REPO_DIR + '/cic'
AOTX_SECURE_JAR_SRC_FILES = GIT_REPO_DIR + '/aotx-secure'
AOTL_PROJECT_JAR_SRC_FILES = GIT_REPO_DIR + '/aotl-project'
JAR_SRC_DIRNAMES = ['ewo', 'cic', 'aotl-project', 'aotx-secure']

REMOTE_BRANCH = 'origin/main' #Examples: SE, WEST, MOKA


def git_fetch(output_dst, rmt_branch, gitdir=GIT_REPO_DIR):
	# TODO: Fetch from SE only
	os.system('cd {} && git fetch && git status > {}/latest_git_status.txt'.format(gitdir, output_dst))

def git_diff(repo, rmt_branch, output_dst, gitdir=GIT_REPO_DIR):
	os.system('cd {} && git fetch && git diff --name-only {} > {}/latest_git_diff.txt'.format(gitdir,rmt_branch, output_dst))
	diff_paths = {
		'A': [],
		'D': [],
		'C': [], #??
		'M': [],
		'R': [],
		'T': [], #??
		'U': []  #??
	}
	diff_objects_by_type = {
		'A': [],
		'D': [],
		'C': [], #??
		'M': [],
		'R': [],
		'T': [], #??
		'U': []  #??
	}

	changes = repo.index.diff(rmt_branch)

	for file_diff in changes:
		print('Type of Change: {}, a_path: {}, b_path: {}'.format(file_diff.change_type, file_diff.a_path, file_diff.b_path))
		# TODO: Filter out filetypes that we don't need to update here
		diff_paths[file_diff.change_type].append((file_diff.a_path, file_diff.b_path))
		diff_objects_by_type[file_diff.change_type].append(file_diff)

	return diff_paths, diff_objects_by_type

def prepare_changes_for_A_or_M(letter, diff_data, dst_root=ROOT_DIR, dry_run=False):
	'''letter can be 'A' or 'M' but none of the other git diff types'''
	# Gather list of directories within the git repo dir. Used in dynamic path processing to get the relative path.
	print("working on: {}".format(letter))

	src_subdirs = {}
	for subdir in os.scandir(GIT_REPO_DIR):
		if subdir.is_dir():
			dir_name = os.path.basename(subdir)
			src_subdirs[dir_name] = len(dir_name)
	src_subdir_names = src_subdirs.keys()

	diff = diff_data[letter]
	dst_path = dst_root
	src_to_dst_pairs = []
	src_path = GIT_REPO_DIR + '/'
	for a_diff in diff:
		src_path += a_diff.a_path

		# Dynamic path processing to get the path used relative to the root directory
		located_in_subdir = False
		for src_sdname in src_subdir_names:
			print(src_subdir_names)
			print(src_sdname == src_path)
			relative_path_index = src_path.find(src_sdname)
			# Handles which subdir to remove from absolute path and convert to relative path
			if relative_path_index != -1:
				# TODO: Check to make sure is actually equal (dirname, dirname_20210803 throws an error for example)
				src_path_by_dir = src_path.split('/')
				if src_sdname == src_path_by_dir[-2]:
					located_in_subdir = True
					print('splitting {} on {}/'.format(src_path, src_sdname))
					rel_path = src_path.split(src_sdname+'/')[1]
					# if dst_root[-1] != '/':
					# 	dst_path += '/'
					dst_path += rel_path
					src_to_dst_pairs.append((src_path, dst_path))
					if dry_run:
						print("src: {} | dst: {}".format(src_path, dst_path))


		# If the added/modified filepath isn't located in a subdirectory of the gitrepo. We place it at root level of the git repo where its supposed to be.
		# located_in_subdir would be true here if the filepath contained a subdir
		# TODO: what if the path contains a subdirname way deeper in the path that matches one of the other subdir names. Then this breaks. Fix.
		if not located_in_subdir:
			print("not located in dir")
			dst_path = dst_root + a_diff.a_path
			print(src_path, dst_path)
			src_to_dst_pairs.append((src_path, dst_path))

		# Reset src and dst paths
		src_path = GIT_REPO_DIR + '/'
		dst_path = dst_root

	return src_to_dst_pairs

def prepare_changes_for_R(diff_data):
	diff = diff_data['R']
	src_dst_pairs_list = []
	for a_diff in diff:
		src = a_diff.a_path
		dst = a_diff.b_path
		src_dst_pairs_list.append((src,dst))
	return src_dst_pairs_list

def prepare_changes_for_D(diff_data):
	diff = diff_data['D']
	src_dst_pairs_list = []
	for a_diff in diff:
		src = a_diff.a_path
		dst = a_diff.b_path
		src_dst_pairs_list.append((src,dst))
	return src_dst_pairs_list


def prepare_to_deploy_changes(diff_data, dst_root=ROOT_DIR, dry_run=False):
	# Setup for all these operations:

	# Gather list of directories within the git repo dir. Used in dynamic path processing to get the relative path.
	src_to_dst_pairs_all = {}
	src_subdirs = {}
	for subdir in os.scandir(GIT_REPO_DIR):
		if subdir.is_dir():
			dir_name = os.path.basename(subdir)
			src_subdirs[dir_name] = len(dir_name)
	src_subdir_names = src_subdirs.keys()


	# HANDLING 'A': FILEPATHS FOR ADDED FILES
	src_to_dst_pairs_all['A'] = prepare_changes_for_A_or_M(
		letter='A',
		diff_data=diff_data,
		dst_root=dst_root,
		dry_run=dry_run
	)


	# HANDLING 'M': FILEPATHS WITH MODIFIED DATA
	src_to_dst_pairs_all['M'] = prepare_changes_for_A_or_M(
		letter='M',
		diff_data=diff_data,
		dst_root=dst_root,
		dry_run=dry_run
	)

	# HANDLING 'R': FILEPATHS THAT HAVE BEEN MOVED / RENAMED
	src_to_dst_pairs_all['R'] = prepare_changes_for_R(diff_data)


	# HANDLING 'D': FILEPATHS THAT NO LONGER EXIST
	src_to_dst_pairs_all['D'] = prepare_changes_for_D(diff_data)

	print('Finished preparing changes')
	return src_to_dst_pairs_all


def deploy_changes_for_A_or_M(src_dst_dict, letter, dry_run=False):
	if dry_run:
		pprint(src_dst_dict)
	else:
		for src, dst in src_dst_dict[letter]:
			os.makedirs(os.path.dirname(dst), exist_ok=True)
			new_path = shutil.copy(src, dst, follow_symlinks=False)

def deploy_changes_for_D(src_dst_dict, dry_run=False):
	if dry_run:
		print('Deleting files below:')
		pprint(src_dst_dict['D'])
	else:
		for src, dst in src_dst_dict['D']:
			if os.path.exists(dst):
				os.remove(dst)
				print('removed: {}'.format(dst))

			else:
				print("The path does not exist: {}".format(dst))

def deploy_changes_for_R(src_dst_dict, dry_run=False):
	if dry_run:
		print('Moving files below:')
		pprint(src_dst_dict)
	else:
		for src, dst in src_dst_dict['R']:
			if os.path.exists(src):
				# os.rename(src, dst)
				os.replace(src, dst)
				print('moved: {} to: {}'.format(src, dst))

			else:
				print("The src path does not exist: {}".format(src))


def run_git_pull(output_dst=ROOT_DIR):
	p = Path(os.getcwd()).parents[0]
	if ROOT_DIR[-1] == '/':
		os.system('cd {} && git pull > {}latest_git_pull.txt'.format(GIT_REPO_DIR, p))

	else:
		os.system('cd {} && git pull > {}/latest_git_pull.txt'.format(GIT_REPO_DIR, p))

def ant_build(path_to_jar_src_code, xml_path, jarname):
	# TODO: write the proper command. Send jars to JAR folder within site specific.
	# xml path is relative to the jar's src code
	print("ant build {}/{} {}".format(path_to_jar_src_code, xml_path, jarname))


def check_for_jar_src_code_changes(src_dst_dict):
	change_types = src_dst_pairs_dict.values()
	for changes in change_types:
		for c in changes:
			src, dst = c
			first_dir = src.split('/')[0]
			if first_dir in JAR_SRC_DIRNAMES:
				return True

	return False



if __name__ == "__main__":
	# Gather, review, and deploy updates from CodeCloud

	# Gathering...
	gr = Repo(GIT_REPO_DIR)
	working_dir = os.getcwd()
	os.system('cd {} && git status > {}/prev_git_status.txt'.format(GIT_REPO_DIR, working_dir))
	git_fetch(output_dst=working_dir, rmt_branch=REMOTE_BRANCH, gitdir=GIT_REPO_DIR)

	# Reviewing changes...
	diff_local_vs_remote_paths, diff_objects = git_diff(repo=gr, output_dst=working_dir,rmt_branch=REMOTE_BRANCH, gitdir=GIT_REPO_DIR)
	src_dst_pairs_dict = prepare_to_deploy_changes(diff_objects,dst_root=ROOT_DIR, dry_run=DRY_RUN)

	if not DRY_RUN:
		# Merge the changes so the files can be copied
		run_git_pull()

		# Deploying updates...
		try:
			deploy_changes_for_A_or_M(src_dst_pairs_dict,letter='A', dry_run=DRY_RUN)
		except:
			e = sys.exc_info()[0]
			print(str(e))
			print('failed to update ADDED files')

		try:
			deploy_changes_for_A_or_M(src_dst_pairs_dict,letter='M', dry_run=DRY_RUN)
		except:
			e = sys.exc_info()[0]
			print(str(e))

			print('failed to update MODIFIED files')

		try:
			deploy_changes_for_R(src_dst_pairs_dict, dry_run=DRY_RUN)
		except:
			e = sys.exc_info()[0]
			print(str(e))

			print('failed to migrate RENAMED files')

		try:
			deploy_changes_for_D(src_dst_pairs_dict, dry_run=DRY_RUN)
		except:
			e = sys.exc_info()[0]
			print(str(e))
			print('failed to DELETE the files removed')


	# pprint(src_dst_pairs_dict)

	# Ant Build to create new Jars
	found_changes_to_jar_src_code = check_for_jar_src_code_changes(src_dst_pairs_dict)
	if found_changes_to_jar_src_code:
		print("\n")
		print("Creating New .jar/.war Files Based on Changes to Source Code")
		path_to_jar_src_code = 'path_to_jar_src_code'
		xml_path = 'xml_path'
		jarname = 'jarname'
		# TODO: Call real JAR / WAR creation commands

		ant_build(path_to_jar_src_code, xml_path, 'ewo')
		ant_build(path_to_jar_src_code, xml_path, 'cic')
		ant_build(path_to_jar_src_code, xml_path, 'aotl-project')
		ant_build(path_to_jar_src_code, xml_path, 'aotx-secure')
		ant_build(path_to_jar_src_code, xml_path, 'war')

		# TODO: Call function from other python script to move all jars/war file sin right repo. (Including inside gitrepo dir!)

		# TODO: Add in commit and push once above is finished so that jars created on the VM are also in code cloud
		now = datetime.utcnow()
		jar_last_updated = str(now).split('.')[0] # Gets current time and date in str format
		msg = "Updated .jars and .war based on latest changes to source code at {} UTC".format(jar_last_updated)
		os.system('cd {} && git add . && git commit -m " {}/prev_git_status.txt'.format(GIT_REPO_DIR, working_dir))
