from json import loads
from flask import request, current_app
from flask_socketio import emit, join_room, leave_room
from app.auth.decorators import authenticated_event
from app.common.exceptions import InvalidOperationException
from test.test_socket import _socket

class SocketService(object):
    """
    Handles operations related to conversations in the
    context of sockets
    """
    
    # maps email address to socket IDs 
    # (both global and conversation)
    _sockets = {}
    
    @staticmethod
    def enter_conversation(conversation_id, participant):
        """
        Adds a participant to a conversation,
        creating a new one if one with the given
        conversation_id does not already exist
        
        :conversation_id  a unique ID for a specific conversation
        :participant      the email address of the participant
        """
        
        if not participant in SocketService._sockets:
            return

        socket_id = SocketService._sockets[participant]['conversation']
        socketio = current_app.extensions['socketio']
        socketio.server.enter_room(socket_id, conversation_id, namespace='/conversation')
        
    @staticmethod
    def _get_conversations(socket_id):
        """
        Provides a list of conversations in which a
        participant is participating
        
        :socket_id     the 'conversation' socket ID for the participant
        """
        
        socketio = current_app.extensions['socketio']
        return socketio.server.rooms(socket_id, namespace='/conversation')
    
    @staticmethod
    def add_global_identifier(email, socket_id):
        """
        Adds the provided socket ID to the internal mapping
        of users to socket IDs
        
        :email        the email address of a user
        :socket_id    the 'global' socket ID for the user
        """
        
        SocketService._sockets[email] = { 'global': socket_id }
    
    @staticmethod
    def add_conversation_identifier(email, socket_id):
        """
        Adds the provided socket ID to the internal mapping
        of users to socket IDs. Raises InvalidOperationException
        if called before add_global_identifier
        
        :email        the email address of a user
        :socket_id    the 'conversation' socket ID for the user
        """
        
        if email not in SocketService._sockets:
            raise InvalidOperationException("The global namespace must be initialized before this namespace")
        SocketService._sockets[email]['conversation'] = socket_id
        
    @staticmethod
    def create_conversation(conversation_id, creator, participants):
        """
        Creates a new conversation, returning a list of the participants
        who were successfully added to the conversation. Users who are not
        online cannot be added to a conversation
        
        
        :conversation_id a unique ID for the new conversation
        :creator         the email address of the conversation's creator
        :participants    a list of email addresses representing the desired participants
        """
        
        result = []
        SocketService._enter_conversation(SocketService._sockets[creator]['conversation'], conversation_id, creator)
        
        for participant in participants:
            if participant in SocketService._sockets:
                global_socket_id = SocketService._sockets[participant]['global']
                conversation_socket_id = SocketService._sockets[participant]['conversation']
                
                # we trick socketIO into thinking that we're in
                # a socket context here so that we can emit what we want
                request.namespace = '/global'
                request.sid = global_socket_id
                
                SocketService._enter_conversation(conversation_socket_id, conversation_id, participant)
                emit('added', {'conversationId': conversation_id, 'creator': creator})
                
                result.append(participant)
                
        return result

    @staticmethod
    def remove_identifier(email):
        """
        Removes the provided email from the internal mapping
        of users to socket IDs
        
        :email        the email address of a user
        """
        
        if email in SocketService._sockets:
            del SocketService._sockets[email]

    @staticmethod
    def leave_conversation(conversation_id, participant):
        """
        Removes a participant from a conversation
        
        :conversation_id  a unique ID for a specific conversation
        :participant      the email address of the participant
        """
        if not participant in SocketService._sockets:
            return

        socket_id = SocketService._sockets[participant]['conversation']
        socketio = current_app.extensions['socketio']
        socketio.server.leave_room(socket_id, conversation_id, namespace='/conversation')

    @staticmethod
    def close_room(conversation_id):
        """
        Removes any users in the given room and deletes room from server

        :conversation_id  a unique ID for a specific conversation
        """

        socketio = current_app.extensions['socketio']
        socketio.server.close_room(conversation_id, namespace = '/conversation')
        

class SocketSetupService(object):
 
    @staticmethod
    def setup_handlers(socketio):
        
        @socketio.on('initialize', namespace="/global")
        @authenticated_event
        def global_init(raw_data, data=None, user=None, error=None):
            if not user:
                emit('error', "Authentication is required to initialize this namespace")
            if error:
                emit('error', error)
                
            SocketService.add_global_identifier(user['email'], request.sid)
            
        @socketio.on('initialize', namespace="/conversation")
        @authenticated_event
        def conversation_init(raw_data, data=None, user=None, error=None):
            if not user:
                emit('error', "Authentication is required to initialize this namespace")
            if error:
                emit('error', error)
            try:
                SocketService.add_conversation_identifier(user['email'], request.sid)
            except InvalidOperationException, e:
                emit('error', e.message)

        @socketio.on('disconnect', namespace="/global")
        @authenticated_event
        def global_disconnect(raw_data, data=None, user=None, error=None):
            if not user:
                emit('error', "Authentication is required to disconnect this namespace")
            if error:
                emit('error', error)
                
            SocketService.remove_identifier(user['email'])

        @socketio.on('updated', namespace="/conversation")
        def conversation_update(json):
            if type(json) is not dict:
                data = loads(json)
            
            emit('updated', data, room=data.get('conversationId'))
             
        @socketio.on('sent', namespace="/conversation")
        def conversation_send(json):
            if type(json) is not dict:
                data = loads(json)

            emit('sent', data, room=data.get("conversationId"))