import os
import json
import urllib2
import base64
import socket
import hou

from hcollections.QDoubleInputDialog import QDoubleInputDialog
from PySide2.QtWidgets import  QMessageBox


class GithubAuthorizator(object):
	defaultdata = {'ver': '1.2', 'collections': [], 'publiccollections': []}
	defaultentry = {'user': '', 'token': ''}
	defaultfilename=os.path.join(os.environ['HOUDINI_USER_PREF_DIR'],'.hpaste_githubcollection')
	#TODO: 2 factor authorization needs to be implemented !!

	@classmethod
	def urlopen_nt(cls, req):
		code = -1
		rep = None
		try:
			rep = urllib2.urlopen(req)
		except urllib2.HTTPError as e:
			code = e.code
		except urllib2.URLError as e:
			raise RuntimeError('unable to reach github: %s' % e.reason)

		if (code == -1): code = rep.getcode()
		return code, rep

	@classmethod
	def readAuthorizationsFile(cls):
		#reads the config file
		#if no config file - creates one

		filepath = cls.defaultfilename
		try:
			with open(filepath, 'r') as f:
				data = json.load(f)
			if ('ver' not in data): raise RuntimeError('file is not good')
		except:
			# file needs to be recreated
			with open(filepath, 'w') as f:
				json.dump(cls.defaultdata, f, indent=4)
			data = dict(cls.defaultdata)  # copy

		return data

	@classmethod
	def newAuthorization(cls,auth=None,altparent=None):
		# appends or changes auth in file
		# auth parameter is used as default data when promped user, contents of auth will get replaced if user logins successfully
		code=0
		if(auth is None):
			auth=dict(GithubAuthorizator.defaultentry) # copy #TODO: this fucksup the question purpose at 74 FIXXXX!!!!

		data=cls.readAuthorizationsFile()
		newauth={}

		while True:
			if(hou.isUIAvailable()):
				btn, (username, password) = hou.ui.readMultiInput('github authorization required. code %d'%code, ('username', 'password'), (1,),  buttons=('Ok', 'Cancel'), initial_contents=(auth['user'],))
			else:
				username, password, btn = QDoubleInputDialog.getUserPassword(altparent,'authorization','github authorization required. code %d'%code,'username','password')
				btn=1-btn
			if(btn!=0):
				if(auth is None):
					return False
				else:
					if(hou.isUIAvailable()):
						btn=hou.ui.displayMessage('Do you want to remove account %s from remembered?'%auth['user'], buttons=('Yes','No'), close_choice=1)
					else:
						btn = QMessageBox.question(altparent,'question','Do you want to remove account %s from remembered?'%auth['user'])
						btn = btn==QMessageBox.No
					if(btn==1):return False
					oldones = [x for x in data['collections'] if x['user'] == auth['user']]
					for old in oldones: data['collections'].remove(old)
					try:
						with open(cls.defaultfilename, 'w') as f:
							json.dump(data, f, indent=4)
					except:
						if (hou.isUIAvailable()):
							hou.ui.displayMessage("writing token to file failed!")
						else:
							QMessageBox.warning(altparent,'error',"writing token to file failed!")
					return False


			for attempt in xrange(10): #really crude way of avoiding conflicts for now
				headers={'User-Agent': 'HPaste', 'Authorization': 'Basic %s' % base64.b64encode('%s:%s' % (username, password))}
				postdata={'scopes':['gist'],'note':'HPaste Collection Access at %s %d'%(socket.gethostname(),attempt)}
				req = urllib2.Request(r'https://api.github.com/authorizations', json.dumps(postdata), headers=headers)
				code, rep = cls.urlopen_nt(req)

				if(code == 201):
					repdata=json.loads(rep.read())

					newauth['token']=repdata['token'] #TODO: check if reply is as expected
					newauth['user']=username
					for key in newauth:auth[key]=newauth[key]
					oldones=[x for x in data['collections'] if x['user']==username]
					for old in oldones: data['collections'].remove(old)
					data['collections'].append(newauth)
					try:
						with open(cls.defaultfilename,'w') as f:
							json.dump(data, f, indent=4)
					except:
						if (hou.isUIAvailable()):
							hou.ui.displayMessage("writing token to file failed!")
						else:
							QMessageBox.warning(altparent,'error', "writing token to file failed!")
					return True
				elif(code == 422):
					#postdata was not accepted
					#so we just make another attempt of creating a token (github requires unique note)
					pass
				elif(code == 401):
					if (hou.isUIAvailable()):
						hou.ui.displayMessage('wrong username or password')
					else:
						QMessageBox.warning(altparent,'error', 'wrong username or password')
					break

			if (hou.isUIAvailable()):
				hou.ui.displayMessage('could not receive token from github. please check and manually delete all HPaste tokens from your github account here: https://github.com/settings/tokens')
			else:
				QMessageBox.warning(altparent, 'error', 'could not receive token from github. please check and manually delete all HPaste tokens from your github account here: https://github.com/settings/tokens')
			return False

	@classmethod
	def testAuthorization(cls,auth):
		#auth is supposed to be a dict returned from listAuthorizations
		#TODO: probably make a dedicatid class
		headers = {'User-Agent': 'HPaste', 'Authorization': 'Token %s' % auth['token']}
		req = urllib2.Request(r'https://api.github.com/user', headers=headers)
		code, rep = cls.urlopen_nt(req)

		return code == 200

	@classmethod
	def listAuthorizations(cls):
		#TODO: Should be moved to a separate module with all kinds of auths
		#should return tuple of authorization dicts

		data=cls.readAuthorizationsFile()

		return tuple(data['collections'])

	@classmethod
	def listPublicCollections(cls):
		data=cls.readAuthorizationsFile()
		return data['publiccollections']