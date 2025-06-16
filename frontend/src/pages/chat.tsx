import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Typography,
  List,
  ListItem,
  Avatar,
  Badge,
  Chip,
  AppBar,
  Toolbar,
  Drawer,
  ListItemButton,
  ListItemAvatar,
  ListItemText,
  Divider,
  InputAdornment,
  Stack,
  useTheme,
  useMediaQuery
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  EmojiEmotions as EmojiIcon,
  Menu as MenuIcon,
  MoreVert as MoreVertIcon,
  Search as SearchIcon,
  Add as AddIcon
} from '@mui/icons-material';
import Header from "../components/Header";

// Mock data - replace with your actual data source
const mockConversations = [
  { id: 1, summary: 'React chat application project discussion', lastMessage: 'That\'s awesome! What kind of project?', timestamp: new Date(Date.now() - 2400000), unread: false },
  { id: 2, summary: 'Weekend plans and movie recommendations', lastMessage: 'Let\'s watch that new sci-fi movie', timestamp: new Date(Date.now() - 86400000), unread: true },
  { id: 3, summary: 'Work meeting follow-up and deadlines', lastMessage: 'The presentation is due Friday', timestamp: new Date(Date.now() - 172800000), unread: false },
];

const mockMessages = [
  { id: 1, senderId: 2, text: 'Hey everyone! How are you doing?', timestamp: new Date(Date.now() - 3600000), status: 'read' },
  { id: 2, senderId: 1, text: 'I\'m doing great! Just finished a big project.', timestamp: new Date(Date.now() - 3000000), status: 'read' },
  { id: 3, senderId: 3, text: 'That\'s awesome! What kind of project?', timestamp: new Date(Date.now() - 2400000), status: 'read' },
  { id: 4, senderId: 1, text: 'A React chat application actually 😊', timestamp: new Date(Date.now() - 1800000), status: 'delivered' },
  { id: 5, senderId: 2, text: 'Nice! I\'d love to see it when it\'s ready.', timestamp: new Date(Date.now() - 600000), status: 'sent' },
];

// Chat Header Component
const ChatHeader = ({ currentUser, onMenuClick }) => (
  <AppBar position="static" color="default" elevation={1}>
    <Toolbar>
      <IconButton
        edge="start"
        onClick={onMenuClick}
        sx={{ mr: 2, display: { md: 'none' } }}
      >
        <MenuIcon />
      </IconButton>
      <Box sx={{ flexGrow: 1 }}>
        <Typography variant="h6" component="div">
          SupplyIQ chat
        </Typography>
      </Box>
      <IconButton>
        <SearchIcon />
      </IconButton>
      <IconButton>
        <MoreVertIcon />
      </IconButton>
    </Toolbar>
  </AppBar>
);

// Individual Message Component
const MessageItem = ({ message, isOwn, sender }) => {
  const theme = useTheme();

  const formatTime = (timestamp) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit'
    }).format(timestamp);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'sent': return theme.palette.grey[400];
      case 'delivered': return theme.palette.grey[600];
      case 'read': return theme.palette.primary.main;
      default: return theme.palette.grey[400];
    }
  };

  return (
    <ListItem
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: isOwn ? 'flex-end' : 'flex-start',
        py: 1
      }}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'flex-end',
          maxWidth: '70%',
          flexDirection: isOwn ? 'row-reverse' : 'row'
        }}
      >
        {!isOwn && (
          <Avatar sx={{ mr: 1, mb: 0.5, width: 32, height: 32 }}>
            {sender?.avatar}
          </Avatar>
        )}
        <Paper
          elevation={1}
          sx={{
            p: 1.5,
            backgroundColor: isOwn ? theme.palette.primary.main : theme.palette.grey[100],
            color: isOwn ? theme.palette.primary.contrastText : theme.palette.text.primary,
            borderRadius: isOwn ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
            maxWidth: '100%',
            wordBreak: 'break-word'
          }}
        >
          <Typography variant="body1">{message.text}</Typography>
        </Paper>
      </Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mt: 0.5,
          alignSelf: isOwn ? 'flex-end' : 'flex-start',
          ml: isOwn ? 0 : 5
        }}
      >
        <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
          {formatTime(message.timestamp)}
        </Typography>
        {isOwn && (
          <Box
            sx={{
              width: 12,
              height: 12,
              borderRadius: '50%',
              backgroundColor: getStatusColor(message.status)
            }}
          />
        )}
      </Box>
    </ListItem>
  );
};

// Message List Component
const MessageList = ({ messages, currentUserId, users }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <List
      sx={{
        flex: 1,
        overflow: 'auto',
        px: 0,
        height: '100%'
      }}
    >
      {messages.map((message) => {
        const sender = users.find(user => user.id === message.senderId);
        const isOwn = message.senderId === currentUserId;
        return (
          <MessageItem
            key={message.id}
            message={message}
            isOwn={isOwn}
            sender={sender}
          />
        );
      })}
      <div ref={messagesEndRef} />
    </List>
  );
};

// Message Input Component
const MessageInput = ({ onSendMessage }) => {
  const [message, setMessage] = useState('');

  const handleSend = () => {
    if (message.trim()) {
      onSendMessage(message);
      setMessage('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Paper
      elevation={3}
      sx={{
        p: 2,
        borderTop: 1,
        borderColor: 'divider'
      }}
    >
      <Stack direction="row" spacing={1} alignItems="flex-end">
        <TextField
          fullWidth
          multiline
          maxRows={4}
          placeholder="Type a message..."
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          variant="outlined"
          size="small"
          InputProps={{
            endAdornment: (
              <InputAdornment position="end">
                <IconButton size="small">
                  <EmojiIcon />
                </IconButton>
                <IconButton size="small">
                  <AttachFileIcon />
                </IconButton>
              </InputAdornment>
            )
          }}
        />
        <IconButton
          color="primary"
          onClick={handleSend}
          disabled={!message.trim()}
          sx={{ mb: 0.5 }}
        >
          <SendIcon />
        </IconButton>
      </Stack>
    </Paper>
  );
};

// User List Sidebar Component
const ConversationList = ({ conversations, selectedConversationId, onConversationSelect, onNewChat }) => {
  const formatTimestamp = (timestamp) => {
    const now = new Date();
    const diff = now - timestamp;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) {
      return new Intl.DateTimeFormat('en-US', {
        hour: '2-digit',
        minute: '2-digit'
      }).format(timestamp);
    } else if (days === 1) {
      return 'Yesterday';
    } else if (days < 7) {
      return `${days} days ago`;
    } else {
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric'
      }).format(timestamp);
    }
  };

  return (
    <Box sx={{ width: 280, height: '100%' }}>
      <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <IconButton
          onClick={onNewChat}
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            width: '100%',
            justifyContent: 'flex-start',
            p: 1,
            borderRadius: 2,
            '&:hover': {
              backgroundColor: 'action.hover'
            }
          }}
        >
          <AddIcon />
          <Typography variant="h6">New Chat</Typography>
        </IconButton>
      </Box>
      <List>
        {conversations.map((conversation) => (
          <ListItemButton
            key={conversation.id}
            selected={selectedConversationId === conversation.id}
            onClick={() => onConversationSelect(conversation.id)}
            sx={{ py: 1.5 }}
          >
            <ListItemText
              primary={
                <Typography
                  variant="body2"
                  sx={{
                    fontWeight: conversation.unread ? 'bold' : 'normal',
                    color: conversation.unread ? 'text.primary' : 'text.secondary'
                  }}
                >
                  {conversation.summary}
                </Typography>
              }
              secondary={
                <Typography variant="caption" color="text.secondary">
                  {formatTimestamp(conversation.timestamp)}
                </Typography>
              }
            />
          </ListItemButton>
        ))}
      </List>
    </Box>
  );
};

// Typing Indicator Component
const TypingIndicator = () => (
  <Box sx={{ p: 2, display: 'flex', alignItems: 'center' }}>
    <Avatar sx={{ mr: 1, width: 24, height: 24 }}>A</Avatar>
    <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
      Alice is typing...
    </Typography>
  </Box>
);

// Main Chat Component
const ChatSystem = () => {
  const [messages, setMessages] = useState(mockMessages);
  const [selectedConversationId, setSelectedConversationId] = useState(1);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [showTyping] = useState(false); // Would be managed by real-time events

  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const currentUserId = 1; // This would come from your auth system

  const handleSendMessage = (text) => {
    const newMessage = {
      id: messages.length + 1,
      senderId: currentUserId,
      text,
      timestamp: new Date(),
      status: 'sent'
    };
    setMessages([...messages, newMessage]);
  };

  const handleNewChat = () => {
    // Clear current messages and start a new conversation
    setMessages([]);
    setSelectedConversationId(null);
    console.log('Starting new chat...');
  };

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const selectedConversation = mockConversations.find(conv => conv.id === selectedConversationId);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      {/* Your existing Header component */}
      <Header />

      <Box sx={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar */}
        <Drawer
          variant={isMobile ? 'temporary' : 'permanent'}
          open={isMobile ? mobileOpen : true}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            '& .MuiDrawer-paper': {
              width: 280,
              boxSizing: 'border-box',
              position: 'relative',
              height: '100%'
            },
          }}
        >
          <ConversationList
            conversations={mockConversations}
            selectedConversationId={selectedConversationId}
            onConversationSelect={setSelectedConversationId}
            onNewChat={handleNewChat}
          />
        </Drawer>

        {/* Main Chat Area */}
        <Box
          sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            height: '100%'
          }}
        >
          <ChatHeader
            currentUser={{ name: selectedConversation?.summary || 'Chat', online: true }}
            onMenuClick={handleDrawerToggle}
          />

          <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <MessageList
              messages={messages}
              currentUserId={currentUserId}
              users={[{ id: 1, avatar: 'U' }, { id: 2, avatar: 'A' }, { id: 3, avatar: 'B' }]}
            />

            {showTyping && <TypingIndicator />}

            <MessageInput onSendMessage={handleSendMessage} />
          </Box>
        </Box>
      </Box>
    </Box>
  );
};

export default ChatSystem;