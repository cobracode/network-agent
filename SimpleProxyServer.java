package ned.apps; 


import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.PrintWriter;
import java.net.ServerSocket;
import java.net.Socket;

public class SimpleProxyServer extends Thread {
    private String host;
    private int remoteport;
    private int localport;
    private ServerSocket ss;
    private boolean loop;

    public SimpleProxyServer(String hostname, int remotePort, int localPort) throws IOException {
        host = hostname;
        remoteport = remotePort;
        localport = localPort;
        ss = null;
        loop = false;
    }

    public boolean isRunning() {
        return loop;
    }

    public void stopRunning() {
        loop = false;
    }

    public void run() {
        System.out.println("SimpleProxyServer::run() begin");
        try {
            loop = true;
            runServer(host, remoteport, localport);
        } catch (Exception e) {
            loop = false;
            e.printStackTrace();
        }
        System.out.println("SimpleProxyServer::run() end");
    }

    private void runServer(String host, int remoteport, int localport) throws IOException {
        System.out.println("SimpleProxyServer::runServer() begin");
        ss = new ServerSocket(localport);
        final byte[] request = new byte[1024];
        byte[] reply = new byte[4096];
        while (loop) {
            Socket client = null, server = null;
            try {
                System.out.println("SimpleProxyServer::runServer(): waiting for client connection on port " + localport);
                // Wait for a connection on the local port
                client = ss.accept();

                System.out.println("SimpleProxyServer::runServer(): client connected");
                final InputStream streamFromClient = client.getInputStream();
                final OutputStream streamToClient = client.getOutputStream();

                // Make a connection to the real server.
                // If we cannot connect to the server, send an error to the
                // client, disconnect, and continue waiting for connections.
                try {
                    server = new Socket(host, remoteport);
                } catch (IOException e) {
                    PrintWriter out = new PrintWriter(streamToClient);
                    out.print("Proxy server cannot connect to " + host + ":"
                            + remoteport + ":\n" + e + "\n");
                    out.flush();
                    client.close();
                    continue;
                }
                // Get server streams.
                final InputStream streamFromServer = server.getInputStream();
                final OutputStream streamToServer = server.getOutputStream();
                // a thread to read the client's requests and pass them
                // to the server. A separate thread for asynchronous.
                Thread t = new Thread() {
                    public void run() {
                        int bytesRead;
                        try {
                            while ((bytesRead = streamFromClient.read(request)) != -1) {
                                streamToServer.write(request, 0, bytesRead);
                                streamToServer.flush();
                            }
                        } catch (IOException e) {
                        }
                        // the client closed the connection to us, so close our
                        // connection to the server.
                        try {
                            streamToServer.close();
                        } catch (IOException e) {
                        }
                    }
                };
                // Start the client-to-server request thread running
                t.start();
                // Read the server's responses
                // and pass them back to the client.
                int bytesRead;
                try {
                    while ((bytesRead = streamFromServer.read(reply)) != -1) {
                        streamToClient.write(reply, 0, bytesRead);
                        streamToClient.flush();
                    }
                } catch (IOException e) {
                }
                // The server closed its connection to us, so we close our
                // connection to our client.
                streamToClient.close();
            } catch (IOException e) {
                System.err.println(e);
            } finally {
                try {
                    if (server != null) server.close();
                    if (client != null) client.close();
                } catch (IOException e) {
                }
            }
        }
    }
}

