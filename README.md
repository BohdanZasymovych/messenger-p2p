# Messenger P2P

A secure, end-to-end encrypted peer-to-peer messaging application with offline message support.

## Project Overview

Messenger P2P is a modern messaging platform that combines the security of end-to-end encryption with the flexibility of both peer-to-peer and server-relayed messaging. Built with privacy and security in mind, it ensures your communications remain private through strong cryptographic algorithms.

### Key Features

- **End-to-End Encryption**: All messages are encrypted using XSalsa20-Poly1305 and Curve25519 elliptic curve cryptography
- **Peer-to-Peer Communication**: Direct WebRTC connections between online users
- **Offline Messaging**: Messages to offline users are encrypted with long-term keys and stored for later retrieval
- **Local Message Storage**: Encrypted database ensures message history is securely preserved
- **Intuitive UI**: Clean and responsive web interface for seamless messaging
- **Docker Deployment**: Easy setup and deployment through containerization

## Technical Architecture

### Backend

- **FastAPI**: High-performance web framework for API endpoints
- **WebSockets**: Real-time bidirectional communication
- **WebRTC**: Peer-to-peer connections with ICE/STUN for NAT traversal
- **PyNaCl**: Cryptographic library for secure encryption
- **PostgreSQL**: Encrypted message and chat storage

### Frontend

- **Vanilla JavaScript**: Clean, framework-free implementation
- **HTML5/CSS3**: Responsive design for desktop environments
- **WebRTC API**: Browser-based peer-to-peer connections

### Security Model

1. **User Authentication**: Password-based authentication with Argon2id key derivation
2. **Local Storage Encryption**: User database encrypted with symmetric XSalsa20-Poly1305
3. **Transport Security**: TLS/SSL for all HTTP and WebSocket connections
4. **Message Encryption**:
   - **Online Users**: Ephemeral key exchange for perfect forward secrecy
   - **Offline Users**: Long-term public key encryption

## How It Works

1. **User Registration/Login**:
   - Create an account with a unique user ID and password
   - Password is hashed with SHA-256 on client side
   - Backend derives encryption keys using Argon2id

2. **Chat Initialization**:
   - Users can create chats with other registered users
   - Long-term public keys are exchanged via server

3. **Messaging Flow**:
   - **When Both Users Online**:
     - Messages encrypted with ephemeral keys
     - Delivered via WebRTC data channel or server relay
   
   - **When Recipient is Offline**:
     - Messages encrypted with recipient's long-term public key
     - Stored on server for later retrieval
     - Delivered when recipient comes online

4. **Message Synchronization**:
   - Frontend periodically polls for new chats and messages
   - Messages are decrypted locally and displayed in UI
   - Date dividers and read indicators provide context

## Setup and Installation

### Prerequisites

- Docker and Docker Compose
- SSL certificates (or use provided self-signed certs for development)
- Environment variables file (.env)

### Environment Variables

Create a `.env` file with the following variables:

### Running the Application

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/messenger-p2p.git
   cd messenger-p2p/client
   ```

2. Create the .env file with environment variables as described above
POSTGRES_USER_CLIENT=postgres POSTGRES_PASSWORD_CLIENT=password POSTGRES_DB_CLIENT=messenger_db DATABASE_URL_CLIENT=postgresql://postgres:password@user_database:5432/messenger_db

3. Create the messenger network in Docker:
```bash
docker network create messenger_network
```

4. Start the application using Docker Compose:
```bash
docker-compose -f user-docker-compose.yml up --build
```

5. Access the application:
https://localhost