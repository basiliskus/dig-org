import argparse

# arguments = [{
#   'name': '',
#   'action': '',
#   'help': ''
# }]


def get_args(description='', arguments=[]):
  parser = argparse.ArgumentParser(description=description)
  for argument in arguments:
    parser.add_argument(
        arguments['name'],
        action=arguments['action'],
        help=arguments['help']
    )
  return parser.parse_args()
