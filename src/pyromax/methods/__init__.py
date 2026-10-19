from .Base import BaseMaxApiMethod
from .SendMessage import SendMessageMethod
from .ForwardMessage import ForwardMessageMethod
from .EditMessage import EditMessageMethod
from .GetMessages import GetMessagesMethod
from .GetChatHistory import GetChatHistoryMethod
from .DeleteMessages import DeleteMessagesMethod
from .PinMessage import PinMessageMethod
from .AddReaction import AddReactionMethod
from .RemoveReaction import RemoveReactionMethod
from .GetReactions import GetReactionsMethod
from .DownloadFile import DownloadFileMethod
from .UploadFile import UploadFileMethod
from .ReadMessage import ReadMessageMethod
from .CreateGroup import CreateGroupMethod
from .InviteUsersToGroup import InviteUsersToGroupMethod
from .RemoveUsersFromGroup import RemoveUsersFromGroupMethod
from .ChangeGroupSettings import ChangeGroupSettingsMethod
from .ChangeGroupProfile import ChangeGroupProfileMethod
from .JoinGroup import JoinGroupMethod, JoinChannelMethod
from .ResolveGroupByLink import ResolveGroupByLinkMethod
from .RevokeInviteLink import RevokeInviteLinkMethod
from .GetChats import GetChatsMethod
from .LeaveGroup import LeaveGroupMethod, LeaveChannelMethod
from .FetchChats import FetchChatsMethod
from .GetJoinRequests import GetJoinRequestsMethod
from .ConfirmJoinRequests import ConfirmJoinRequestsMethod
from .DeclineJoinRequests import DeclineJoinRequestsMethod
from .DeleteChat import DeleteChatMethod
from .AddAdmin import AddAdminMethod
from .Set2Fa import Set2FaMethod
from .Remove2Fa import Remove2FaMethod
from .ChangePassword import ChangePasswordMethod
from .Check2Fa import Check2FaMethod
from .ApproveQrLogin import ApproveQrLoginMethod
from .ChangeProfile import ChangeProfileMethod
from .CreateFolder import CreateFolderMethod
from .GetFolders import GetFoldersMethod
from .UpdateFolder import UpdateFolderMethod
from .DeleteFolders import DeleteFoldersMethod
from .CloseAllSessions import CloseAllSessionsMethod
from .Logout import LogoutMethod
from .SetPresence import SetPresenceMethod
from .GetMembersByIds import GetMembersByIdsMethod
from .GetUsers import GetUsersMethod
from .SearchByPhone import SearchByPhoneMethod
from .GetSessions import GetSessionsMethod
from .GetChatId import GetChatIdMethod
from .AddContact import AddContactMethod
from .RemoveContact import RemoveContactMethod
from .ImportContacts import ImportContactsMethod
from .CreatePoll import CreatePollMethod
from .VotePoll import VotePollMethod
from .ChangeProfileSettings import ChangeProfileSettingsMethod
from .SendComment import SendCommentMethod
from .FetchComments import FetchCommentsMethod
from .EditComment import EditCommentMethod
from .DeleteComment import DeleteCommentMethod
from .AddCommentReaction import AddCommentReactionMethod
from .SetChannelComments import SetChannelCommentsMethod
from .GetComment import GetCommentMethod
from .GetComments import GetCommentsMethod
from .RemoveCommentReaction import RemoveCommentReactionMethod
from .SubscribeComments import SubscribeCommentsMethod
from .GetCommentsInfo import GetCommentsInfoMethod
from .DeleteUserComments import DeleteUserCommentsMethod
from .BlockCommentAuthor import BlockCommentAuthorMethod

__all__ = [
    "BaseMaxApiMethod",
    "SendMessageMethod",
    "ForwardMessageMethod",
    "EditMessageMethod",
    "GetMessagesMethod",
    "GetChatHistoryMethod",
    "DeleteMessagesMethod",
    "PinMessageMethod",
    "AddReactionMethod",
    "RemoveReactionMethod",
    "GetReactionsMethod",
    "ReadMessageMethod",
    "DownloadFileMethod",
    "UploadFileMethod",
    "CreateGroupMethod",
    "InviteUsersToGroupMethod",
    "RemoveUsersFromGroupMethod",
    "ChangeGroupSettingsMethod",
    "ChangeGroupProfileMethod",
    "JoinGroupMethod",
    "JoinChannelMethod",
    "ResolveGroupByLinkMethod",
    "RevokeInviteLinkMethod",
    "GetChatsMethod",
    "LeaveGroupMethod",
    "LeaveChannelMethod",
    "FetchChatsMethod",
    "GetJoinRequestsMethod",
    "ConfirmJoinRequestsMethod",
    "DeclineJoinRequestsMethod",
    "DeleteChatMethod",
    "AddAdminMethod",
    "Set2FaMethod",
    "Remove2FaMethod",
    "ChangePasswordMethod",
    "Check2FaMethod",
    "ApproveQrLoginMethod",
    "ChangeProfileMethod",
    "CreateFolderMethod",
    "GetFoldersMethod",
    "UpdateFolderMethod",
    "DeleteFoldersMethod",
    "CloseAllSessionsMethod",
    "LogoutMethod",
    "SetPresenceMethod",
    "ChangeProfileSettingsMethod",
    "GetMembersByIdsMethod",
    "GetUsersMethod",
    "SearchByPhoneMethod",
    "GetSessionsMethod",
    "AddContactMethod",
    "RemoveContactMethod",
    "ImportContactsMethod",
    "GetChatIdMethod",
    "CreatePollMethod",
    "VotePollMethod",
    "SendCommentMethod",
    "FetchCommentsMethod",
    "EditCommentMethod",
    "DeleteCommentMethod",
    "AddCommentReactionMethod",
    "SetChannelCommentsMethod",
    "GetCommentMethod",
    "GetCommentsMethod",
    "RemoveCommentReactionMethod",
    "SubscribeCommentsMethod",
    "GetCommentsInfoMethod",
    "DeleteUserCommentsMethod",
    "BlockCommentAuthorMethod",
]
