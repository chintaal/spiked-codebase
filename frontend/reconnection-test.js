// Meeting Bot Reconnection Test Script
// Run this in browser console to test reconnection logic step by step

async function testReconnection() {
    console.log('=== MEETING BOT RECONNECTION TEST ===');
    
    // Step 1: Check localStorage
    console.log('Step 1: Checking localStorage...');
    const savedUrl = localStorage.getItem('currentMeetingUrl');
    console.log('Saved URL:', savedUrl);
    
    // Step 2: Set test URL if none exists
    if (!savedUrl) {
        console.log('Step 2: Setting test URL...');
        const testUrl = 'https://meet.google.com/tjc-kxof-eoc';
        localStorage.setItem('currentMeetingUrl', testUrl);
        console.log('Set test URL:', testUrl);
    }
    
    // Step 3: Validate URL
    console.log('Step 3: Validating URL...');
    const urlToTest = savedUrl || localStorage.getItem('currentMeetingUrl');
    const googleMeetRegex = /meet\.google\.com\/([a-z0-9-]+)/i;
    const match = urlToTest.match(googleMeetRegex);
    
    if (match) {
        const validation = {
            platform: 'google_meet',
            meetingId: match[1],
            isValid: true
        };
        console.log('URL validation successful:', validation);
        
        // Step 4: Check bot status
        console.log('Step 4: Checking bot status...');
        try {
            const response = await fetch('http://localhost:8000/vexa/bots/status');
            const botData = await response.json();
            console.log('Bot status response:', botData);
            
            // Step 5: Find matching bot
            console.log('Step 5: Looking for matching bot...');
            const runningBots = botData.running_bots || [];
            const existingBot = runningBots.find(bot => 
                bot.native_meeting_id === validation.meetingId && 
                bot.platform === validation.platform
            );
            
            if (existingBot) {
                console.log('✅ Found existing bot for reconnection:', existingBot);
                console.log('Reconnection should work!');
                
                // Step 6: Test transcript fetch
                console.log('Step 6: Testing transcript fetch...');
                try {
                    const transcriptResponse = await fetch(`http://localhost:8000/vexa/bots/google_meet/${validation.meetingId}/transcript`);
                    const transcript = await transcriptResponse.json();
                    console.log('Transcript fetch result:', transcript);
                } catch (error) {
                    console.log('Transcript fetch failed:', error.message);
                }
                
            } else {
                console.log('❌ No existing bot found for meeting ID:', validation.meetingId);
                console.log('Available bots:', runningBots.map(bot => ({
                    id: bot.native_meeting_id,
                    platform: bot.platform
                })));
            }
            
        } catch (error) {
            console.log('❌ Bot status check failed:', error.message);
        }
        
    } else {
        console.log('❌ URL validation failed for:', urlToTest);
    }
    
    console.log('=== TEST COMPLETE ===');
}

// Auto-run the test
testReconnection();
