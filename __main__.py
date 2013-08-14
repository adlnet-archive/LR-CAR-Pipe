import argparse, json, sys

import car_pipe as cp

# the list of documents to publish
car_docs = []
publish_payload = []

def main():

	# parse arguments
	parser = argparse.ArgumentParser()

	parser.add_argument('command',
		help='The action to apply to the document',
		choices=['view','convert','publish'])

	parser.add_argument('doc_id',
		help='A CAR document ID, "all", or "updates"')
	# key = '100.ATSC/0721EED9-F5C8-493D-93D7-D51EB0BB2A24-1335889302182'

	parser.add_argument('--car-file', '-cf',
		help='Save the CAR envelope to a file')
	parser.add_argument('--lr-file', '-lf',
		help='Save the LR envelope to a file if generated')
	#parser.add_argument('--log-file',
	#	help='Write output to file instead of stdout',
	#	type=argparse.FileType('w'), default=sys.stdout)

	parser.add_argument('--verbose', '-v',
		help='Print initial and converted metadata payloads',
		action='store_true')

	parser.add_argument('--overwrite', dest='overwrite',
		help='On conflict, replace old LR envelope with new one',
		action='store_true', default=None)
	parser.add_argument('--no-overwrite', dest='overwrite',
		help='On conflict, do not push generated LR envelope',
		action='store_false', default=None)

	parser.add_argument('--publish-chunk-size', '-c',
		help='For "all" or "updates", select number of documents contained in a single push to the LR',
		type=int, default=50)
	parser.add_argument('--update-window', '-w',
		help='For "updates", publish all documents updated within UPDATE_WINDOW days',
		type=int, default=2)

	args = parser.parse_args()

	# parse and process document id
	if args.doc_id.lower() == 'all':
		car_docs = cp.get_CAR_documents()
		for doc in car_docs:
			processDocument(doc, args)


	elif args.doc_id.lower() == 'updates':
		car_docs = cp.get_CAR_documents(days_old=args.update_window)
		for doc in car_docs:
			processDocument(doc, args)
	
	else:
		car_docs = [cp.get_CAR_document(args.doc_id)]
		processDocument(car_docs[0], args)

	# publish the accumulated payload in chunks of 50
	total_ok = True
	total_error = []

	chunk = args.publish_chunk_size
	for batch in [publish_payload[i:i+chunk] for i in range(0,len(publish_payload),chunk)]:
		status = cp.publish_documents(publish_payload)

		# print status messages
		for i,doc_status in enumerate(status['document_results']):
			if doc_status['OK']:
				print 'Document', car_docs[i]['id'], 'published as', doc_status['doc_ID']
			else:
				print 'Document', car_docs[i]['id'], 'failed:', doc_status['error']

		total_ok &= status['OK']
		if not status['OK']:
			total_error.append( status['error'] )

	if len(publish_payload) > 0:
		if total_ok:
			print
			print 'Publish successful'
		else:
			print
			print 'Error:', total_error

	print
	print 'Done'


def processDocument( cardoc, args ):

	# all commands do this; view only does this

	# dump metadata to file and/or/nor screen
	if args.car_file != None:
		cp.dump_to_file(args.car_file, cardoc);
	if args.command == 'view' or args.verbose:
		print 10*'*', 'Input', 10*'*'
		print json.dumps(cardoc, indent=4)

	# only proceed if document must be converted
	if args.command in ['convert','publish']:
		
		# convert CAR metadata to LR metadata
		lrmi = cp.to_LRMI(cardoc)
		envelope = cp.to_LR(lrmi, car_id=cardoc['id'])
		
		# dump metadata to file and/or/nor screen
		if args.lr_file != None:
			cp.dump_to_file(args.lr_file, envelope)
		if args.command == 'convert' or args.verbose:
			print 10*'*', 'Output', 10*'*'
			print json.dumps(envelope, indent=4)

		# only proceed if document must be published
		if args.command == 'publish':

			# check if document already exists
			oldDoc = cp.get_LR_from_CAR_id(cardoc['id'])

			if oldDoc != None:
				oldId = oldDoc['doc_ID']

				if args.overwrite == None:

					# compare old doc to new (minus generated fields)
					del oldDoc['digital_signature']
					del oldDoc['_rev']
					del oldDoc['node_timestamp']
					del oldDoc['create_timestamp']
					del oldDoc['update_timestamp']
					del oldDoc['publishing_node']
					del oldDoc['_id']
					del oldDoc['doc_ID']
					comp = cp.recursive_compare(oldDoc, envelope);

					# prompt the user for action
					print 'Another document with same CAR ID already in LR ({}).'.format(oldId)
					print 'Additions:'
					print 'Old doc', json.dumps(comp[0], indent=4)
					print 'New doc', json.dumps(comp[1], indent=4)
					response = raw_input('Replace? ')
					if response.lower() in ['yes','y']:
						envelope['replaces'] = [oldId]
						publish_payload.append(envelope)
						#id = cp.publish_document(envelope)
						#if id != None:
						#	print 'Published {} to LR; id {}'.format(cardoc['id'], id)

				elif args.overwrite == True:
					envelope['replaces'] = [oldId]
					publish_payload.append(envelope)
					#id = cp.publish_document(envelope)
					#if id != None:
					#	print 'Published {} to LR; id {}'.format(cardoc['id'], id)

				else:
					print 'Document {} duplicates {}, skipping.'.format(cardoc['id'], oldDoc['doc_ID'])

			else:
				publish_payload.append(envelope)
				#id = cp.publish_document(envelope)
				#if id != None:
				#	print 'Published {} to LR; id {}'.format(cardoc['id'], id)



if __name__ == '__main__':
	main()
