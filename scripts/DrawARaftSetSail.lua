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
local ScreenGui = Instance.new("ScreenGui")
local Frame = Instance.new("Frame")
local TextButton = Instance.new("TextButton")

ScreenGui.Parent = game.Players.LocalPlayer:WaitForChild("PlayerGui")
ScreenGui.ZIndexBehavior = Enum.ZIndexBehavior.Sibling

Frame.Parent = ScreenGui
Frame.BackgroundColor3 = Color3.fromRGB(0, 0, 0)
Frame.BorderColor3 = Color3.fromRGB(89, 89, 89)
Frame.BorderSizePixel = 0
Frame.Position = UDim2.new(0.626645386, 0, 0.0163934417, 0)
Frame.Size = UDim2.new(0, 304, 0, 100)
Frame.Active = true
Frame.Draggable = true 

TextButton.Parent = Frame
TextButton.BackgroundColor3 = Color3.fromRGB(119, 41, 255)
TextButton.BorderColor3 = Color3.fromRGB(0, 0, 0)
TextButton.BorderSizePixel = 0
TextButton.Position = UDim2.new(0.171052635, 0, 0.25, 0)
TextButton.Size = UDim2.new(0, 200, 0, 50)
TextButton.Font = Enum.Font.SourceSans
TextButton.Text = "Loop TP to End"
TextButton.TextColor3 = Color3.fromRGB(0, 0, 0)
TextButton.TextSize = 14.000


local TargetPosition = CFrame.new(-1926.07764, 4.82699966, -54.3953018, 1, 0, 0, 0, 1, 0, 0, 0, 1) 

local tpActive = false

TextButton.MouseButton1Click:Connect(function()
    tpActive = not tpActive
    
    if tpActive then
        TextButton.Text = "Teleporting..."
        TextButton.BackgroundColor3 = Color3.fromRGB(50, 255, 50) -- Green
        
        task.spawn(function()
            while tpActive do
                local char = game.Players.LocalPlayer.Character
                if char and char:FindFirstChild("HumanoidRootPart") then
                    char.HumanoidRootPart.CFrame = TargetPosition
                end
                task.wait()
            end
        end)
    else
        TextButton.Text = "Loop TP to End"
        TextButton.BackgroundColor3 = Color3.fromRGB(119, 41, 255) -- Purple
    end
end)
