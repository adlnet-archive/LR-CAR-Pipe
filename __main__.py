import argparse, json

import car_pipe as cp

def main():

	# parse arguments
	parser = argparse.ArgumentParser()

	parser.add_argument('command',
		help='The action to apply to the document',
		choices=['view','convert','publish'])

	parser.add_argument('doc_id',
		help='A CAR document ID')
	# key = '100.ATSC/0721EED9-F5C8-493D-93D7-D51EB0BB2A24-1335889302182'

	parser.add_argument('--car-file', '-cf',
		help='Save the CAR envelope to a file')
	parser.add_argument('--lr-file', '-lf',
		help='Save the LR envelope to a file if generated')
	parser.add_argument('--verbose', '-v',
		help='Print initial and converted metadata payloads',
		action='store_true')

	args = parser.parse_args()

	# all commands do this; view only does this

	# retrieve CAR metadata
	cardoc = cp.getCARDocument(args.doc_id)

	# dump metadata to file and/or/nor screen
	if args.car_file != None:
		cp.dumpToFile(args.car_file, cardoc);
	if args.command == 'view' or args.verbose:
		print 10*'*', 'Input', 10*'*'
		print json.dumps(cardoc, indent=4)

	# only proceed if document must be converted
	if args.command in ['convert','publish']:
		
		# convert CAR metadata to LR metadata
		lrmi = cp.toLRMI(cardoc)
		envelope = cp.toLR(lrmi, id=cardoc['id'])
		
		# dump metadata to file and/or/nor screen
		if args.lr_file != None:
			cp.dumpToFile(args.lr_file, envelope)
		if args.command == 'convert' or args.verbose:
			print 10*'*', 'Output', 10*'*'
			print json.dumps(envelope, indent=4)

		# only proceed if document must be published
		if args.command == 'publish':

			cp.publishDocument(envelope)
		

	print
	print
	print 'Done'

if __name__ == '__main__':
	main()
