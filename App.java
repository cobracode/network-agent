package ned.apps;

import java.io.IOException;

public class App 
{
    public static void main(final String[] args)
    {
        System.out.println("App.main() begin");

        try {
            SimpleProxyServer sps = new SimpleProxyServer("www.google.com", 80, 5555);
            sps.run();
        }
        catch (final IOException e) {
            System.out.println("IOException: " + e.getMessage());
            e.printStackTrace();
        }


        System.out.println("App.main() end");
    }
}
