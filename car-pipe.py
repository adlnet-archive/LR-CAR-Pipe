#!/bin/env python
from urllib2 import Request, urlopen, URLError
from urllib import urlencode
from lxml import etree
import json
import sys
import datetime as dt

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
	

def main(params):

	# get list of possible refinements
	if 'refinements' in params:
		data = getData('/catalogitems/refinements')
		for category in data['categories']:
			print '{} ({})'.format(category['about'], category['refinements'][0]['name'])
			print '\t',
			for ref in category['refinements']:
				print ref['value']+',',
			print

	# get metadata for documents
	if 'saveFreeMetadata' in params:
		data = getData('/catalogitems', distributionrestriction='A', field_list='identifier,formats')
		metadata = []
		for document in data['catalogitems']:
			for f in document['formats']:
				if f['path'] == 'metadata.xml':
					metadata.append(document)

		# retrieve metadata from available documents
		md = metadata[0]
		mdlink = ''
		for f in md['formats']:
			if f['path'] == 'metadata.xml':
				mdlink = f['link']['href']

		xml = getData( mdlink, 'application/xml' )
		ofp = open('data/'+md['identifier']+'-metadata.xml', 'w')
		ofp.write( etree.tostring(xml) )
		ofp.close()
			

	if 'saveDocs' in params:

		field_list = 'id,status,title,summary,aliases,approvaldate,postdate,discoverable,new,restricted,official,catalogtype,producttype,knowledgecenter,distributionrestriction,poc,keyword,jobspeciality,links,formats,download'
		docs = getData('/catalogitems', distributionrestriction='A', status='R', field_list=field_list, pagesize=25)
		for doc in docs['catalogitems']:
			ofp = open('data/'+doc['id'].replace('/','_')+'.json', 'w')
			ofp.write( json.dumps(doc, indent=4) )
			ofp.close()

	if 'getDoc' in params:

		# retrieve document from army registry
		field_list = 'id,status,identifier,title,summary,postdate,catalogtype,producttype,knowledgecenter,distributionrestriction,poc,keywords,jobspeciality,formats'
		keys = [
			'100.ATSC/1C68769C-ADAD-450E-A7C3-7FFA73E027BD-1362536487263',
			'100.ATSC/22F3C59A-4ABD-4D9E-A1BE-E80B188FD1AC-1373890928670',
			'100.ATSC/2E53554D-6208-43FD-BA1E-193F8F9D7882-1373394427795'
		]

		if len(params) > 1:
			keys = params[1:]

		for key in keys:
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

			#print json.dumps(doc, indent=4, sort_keys=True)

	print 'Done'

def toLR(metadata):

	document = {
		'doc_type': 'resource_data',
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

if __name__ == '__main__':
	main(sys.argv[1:])
