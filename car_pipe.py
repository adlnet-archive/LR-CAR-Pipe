#!/bin/env python
from urllib2 import Request, urlopen, URLError
from urllib import urlencode
from lxml import etree
import json
import sys
import datetime as dt
import time
import oauth2 as oauth

def getData(page, mime = 'application/json', **kwargs):

	# build URL
	if page[0] == '/':
		url = 'https://rdl.train.army.mil/catalog/api' + page
	else:
		url = page

	# add arguments if appropriate
	if len(kwargs) > 0:
		url += '?' + urlencode(kwargs)

	print 'Retrieving', url
	request = Request(url, headers = {'Accept': mime})
	try:
		io = urlopen(request)
		if mime == 'application/json':
			data = json.loads(io.read())
		elif mime == 'application/xml':
			data = etree.parse(io)
		else:
			data = io.read()
	except Exception as e:
		print e
		return

	return data


def getRefinements():
	'''get list of possible refinements'''

	data = getData('/catalogitems/refinements')
	for category in data['categories']:
		print '{} ({})'.format(category['about'], category['refinements'][0]['name'])
		print '\t',
		for ref in category['refinements']:
			print ref['value']+',',
		print


def getCarDocuments():
	'''get sample set of CAR metadata'''

	field_list = 'id,status,title,summary,aliases,approvaldate,postdate,discoverable,new,restricted,official,catalogtype,producttype,knowledgecenter,distributionrestriction,poc,keyword,jobspeciality,links,formats,download'
	docs = getData('/catalogitems', distributionrestriction='A', status='R', field_list=field_list, pagesize=25)
	for doc in docs['catalogitems']:
		ofp = open('data/'+doc['id'].replace('/','_')+'.json', 'w')
		ofp.write( json.dumps(doc, indent=4) )
		ofp.close()


def convertDocument(key):

	# retrieve document from army registry
	field_list = 'id,status,identifier,title,summary,postdate,catalogtype,producttype,knowledgecenter,distributionrestriction,poc,keywords,jobspeciality,formats'

	doc = getData('/catalogitem/'+key, field_list=field_list)
	doc = doc['catalogitem']

	lrmi = toLRMI(doc)
	envelope = toLR(lrmi)		

	# write to file
	ofp = open('data/'+doc['title'].replace('/','_')+'-original.json', 'w')
	ofp.write( json.dumps(doc, indent=4) )
	ofp.close()
	ofp = open('data/'+doc['title'].replace('/','_')+'-envelope.json', 'w')
	ofp.write( json.dumps(envelope, indent=4) )
	ofp.close()

	return envelope


def publishDocument(doc):

	publish_packet = {
		'documents': [doc]
	}
	params = {
		'oauth_version': '1.0',
		'oauth_nonce': oauth.generate_nonce(),
		'oauth_timestamp': int(time.time())
	}
	consumer = oauth.Consumer('steve.vergenz.ctr@adlnet.gov', 'lws48mTjMySQovJy3qKKqGWr3uxmMdrk')
	token = oauth.Token('node_sign_token', 'RGIf9sKHVOOcJuZIQaDacwxTejvSqnPq')
	client = oauth.Client(consumer,token)
	response, content = client.request(
		'http://sandbox.learningregistry.org/publish',
		method = 'POST',
		body = json.dumps(publish_packet),
		headers = {'Content-Type': 'application/json'}
	)
	print response
	print content



def toLR(metadata):
	'''generate an LR envelope based on LRMI metadata'''

	document = {
		'doc_type': 'resource_data',
		'doc_version': '0.49.0',
		'active': True,
		'TOS': {
			'submission_TOS': 'http://www.learningregistry.org/tos/cc0/v0-5'
		},

		'resource_data_type': 'metadata',
		'payload_placement': 'inline',
		'payload_schema': ['LRMI'],
		'resource_data': metadata,

		'keys': metadata['properties']['keywords'],
		'resource_locator': metadata['properties']['url'],

		'identity': {
			'owner': metadata['properties']['publisher']['properties']['name'],
			'curator': 'Central Army Registry (CAR)',
			'submitter': 'ADL',
			'signer': 'ADL',
			'submitter_type': 'agent'
		}
	}

	return document


def toLRMI(carDoc):
	'''generate LRMI metadata based on CAR metadata'''

	# pull in general information
	document = {
		'type': 'http://schema.org/CreativeWork',
		'properties': {
			'name': carDoc['title'],
			'author': {
				'type': 'http://schema.org/Person',
				'properties': {
					'email': carDoc['poc']['email'],
					'memberOf': {
						'type': 'http://schema.org/Organization',
						'properties': {
							'name': carDoc['poc']['organization']
						}
					}
				}
			},
			'description': carDoc['summary'],
			'keywords': carDoc['keywords'],
			'mediaType': [carDoc['producttype']['title']],
			'publisher': {
				'type': 'http://schema.org/Organization',
				'properties': {
					'name': carDoc['knowledgecenter']['title']
				}
			},
			'useRightsUrl': 'http://adlnet.gov/distribution-statement/'+carDoc['distributionrestriction']['code'].lower()+'/'
		}
	}

	# detect language from product type
	if 'Spanish Language' not in carDoc['producttype']['title']:
		document['properties']['inLanguage'] = 'en'
	else:
		document['properties']['inLanguage'] = 'es'

	# reorganize date string
	parts = [int(i) for i in carDoc['postdate'].split('/')]
	d = dt.date(parts[2], parts[0], parts[1])
	document['properties']['datePublished'] = d.isoformat()

	# set distribution statement

	# find the document link in the formats field
	for f in carDoc['formats']:
		if f['link']['rel'] == 'self':
			document['properties']['url'] = f['link']['href']

	return document

