import argparse

import car_pipe

def main():

	# parse arguments
	parser = argparse.ArgumentParser()
	parser.add_argument('command',
		help='The action to apply to the document',
		choices=['view','convert','publish'],
		default='view')
	parser.add_argument('doc_id', help='A CAR document ID')
	args = parser.parse_args()

	#if len(params) > 1:
	#	key = params[1]
	#else:
	#	key = '100.ATSC/0721EED9-F5C8-493D-93D7-D51EB0BB2A24-1335889302182'

	#if params[0] == 'getRefinements':
	#	getRefinements()

	#elif params[0] == 'saveDocs':
	#	getCarDocuments()

	#elif params[0] == 'convertDoc':
	#	convertDocument(key)

	#elif params[0] == 'convertAndPublish':
	#	envelope = convertDocument(key)
	#	publishDocument(envelope)
		
	#else:
	#	print 'Help information'

	#print 'Done'

if __name__ == '__main__':
	main()
