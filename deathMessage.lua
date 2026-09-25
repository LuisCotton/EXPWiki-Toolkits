local p = {}

local dataCache

local function loadData()
    if dataCache then
        return dataCache
    end

    local ok, data = pcall(mw.loadJsonData, 'DeathMessage.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('DeathMessage.json')
        if not title or not title.exists then
            return nil
        end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then
            return nil
        end
    end

    dataCache = {}
    for _, item in ipairs(data.entries or data) do
        if type(item) == 'table' and type(item.deathMessage) == 'string' then
            if type(item.id) == 'string' and item.id ~= '' then
                dataCache[item.id] = item.deathMessage
                dataCache[item.id:lower()] = item.deathMessage
            end
            if type(item.name) == 'string' and item.name ~= '' then
                dataCache[item.name] = item.deathMessage
                dataCache[item.name:lower()] = item.deathMessage
            end
        end
    end
    return dataCache
end

local function formatMessage(message)
    return message:gsub('\\n', '<br>'):gsub('\r\n', '<br>'):gsub('[\r\n]', '<br>')
end

function p.getDeathMessage(frame)
    local data = loadData()
    if not data then
        return ''
    end

    local query = mw.text.trim(tostring(frame.args[1] or ''))
    if query == '' then
        return ''
    end

    local message = data[query] or data[query:lower()]
    return message and formatMessage(message) or ''
end

return p