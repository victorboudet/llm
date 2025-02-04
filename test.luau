-- Initialize variable 'a'
local a = 0

-- Define the function 'test' to modify 'a'
function test()
    -- Localize 'a' within the function scope
    local a = 1
end

-- Call the function 'test'
test()

-- Print the value of 'a' to verify it remains unchanged outside 'test'
print(a)  -- Output should be 0, as 'a' is localized in 'test'
