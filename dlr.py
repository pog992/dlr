#!/usr/bin/env python
from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor


class CommandReceiver(LineReceiver):

	delimiter = '\n'

	def lineReceived(self, line):
		cmdargs = line.split()
		if cmdargs:
			self.commandReceived(cmdargs[0], *cmdargs[1:])

	def commandReceived(self, command, *args):
		raise NotImplementedError


class ProtocolError(Exception):
	def __init__(self, errno, desc):
		super(ProtocolError, self).__init__('%d %s' % (errno, desc))

class BadCredentials(ProtocolError):
	def __init__(self):
		super(BadCredentials, self).__init__(1, "bad login or password")

class UnknownCommand(ProtocolError):
	def __init__(self):
		super(UnknownCommand, self).__init__(2, "unknown command")

class BadFormat(ProtocolError):
	def __init__(self):
		super(BadFormat, self).__init__(3, "bad format")

# class TooManyArguments(ProtocolError):
# 	def __init__(self):
# 		super(TooManyArguments, self).__init__(4, "too many arguments")

class InternalError(ProtocolError):
	def __init__(self):
		super(InternalError, self).__init__(5, "internal error, sorry...")

class CommandsLimit(ProtocolError):
	def __init__(self):
		super(CommandsLimit, self).__init__(6, "commands limit reached, forced waiting activated")


def handle_protocol_errors(method):
	def new_method(self, *args, **kwargs):
		try:
			method(self, *args, **kwargs)
		except ProtocolError as e:
			self.sendLine('FAILED %s' % e)
	return new_method


class DeadlineProtocol(CommandReceiver):

	__slots__ = ('authenticator', 'user_handler', 'username')

	def __init__(self, authenticator):
		self.authenticator = authenticator
		self.user_handler = None
		self.username = None

	def connectionMade(self):
		self.sendLine('LOGIN')

	def connectionLost(self, reason):
		if self.user_handler:
			self.user_handler.connectionLost()

	def ack(self):
		self.sendLine('OK')

	@handle_protocol_errors
	def commandReceived(self, command, *args):
		print command, args
		if self.user_handler:
			cmdu = command.upper()
			try:
				method = getattr(self.user_handler, 'command_%s' % cmdu)
				gen = method(*args)
			except AttributeError:
				raise UnknownCommand
			except TypeError:
				raise BadFormat
			else:
				for line in gen:
					self.sendLine(line)
				self.ack()
		elif not self.username:
			self.username = command
			self.sendLine('PASS')
		else:
			password = command
			self.user_handler = self.authenticator(self.username, password)
			self.ack()
		

class DictAuthenticator(object):

	def __init__(self, users=None):
		self.users = users

	def __call__(self, username, password):
		return Task()


class Task(object):
	def connectionLost(self):
		pass

	def command_SAY(self, text):
		yield text


class DeadlineProtocolFactory(Factory):

	def __init__(self):
		pass

	def buildProtocol(self, addr):
		return DeadlineProtocol(DictAuthenticator())


if __name__ == '__main__':
	reactor.listenTCP(8123, DeadlineProtocolFactory())
	reactor.run()
