task.spawn(function()
    local req = (syn and syn.request) or (http and http.request) or http_request or (fluxus and fluxus.request) or request
    
    if req then
        req({
            Url = 'http://127.0.0.1:6463/rpc?v=1',
            Method = 'POST',
            Headers = {
                ['Content-Type'] = 'application/json',
                ['Origin'] = 'https://discord.com'
            },
            Body = game:GetService("HttpService"):JSONEncode({
                cmd = 'INVITE_BROWSER',
                nonce = game:GetService("HttpService"):GenerateGUID(false),
                args = {code = 'r6JW6FBMwU'} 
            })
        })
    end
end)

while true do
    local args1 = {
        {
            type = "SeaCreature",
            rarity = "Common",
            creatureId = 1,
            color = Color3.new(0.8313725590705872, 0.8313725590705872, 0.8313725590705872),
            value = 1,
            icon = "\240\159\144\162",
            displayName = "Mosasaurus"
        }
    }
    game:GetService("ReplicatedStorage"):WaitForChild("GrantReward"):InvokeServer(unpack(args1))

    local args2 = {
        {
            type = "Money",
            rarity = "Common",
            color = Color3.new(0.8313725590705872, 0.8313725590705872, 0.8313725590705872),
            value = 2000,
            icon = "\240\159\146\176",
            displayName = "10,000 Cash"
        }
    }
    game:GetService("ReplicatedStorage"):WaitForChild("GrantReward"):InvokeServer(unpack(args2))

    local args3 = {
        {
            type = "PaddleBoost",
            rarity = "Common",
            color = Color3.new(0.8313725590705872, 0.8313725590705872, 0.8313725590705872),
            value = 1,
            icon = "\226\154\161",
            displayName = "Paddle Boost"
        }
    }
    game:GetService("ReplicatedStorage"):WaitForChild("GrantReward"):InvokeServer(unpack(args3))
end
