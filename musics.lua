local p = {}

local dataCache

local function loadData()
    if dataCache then
        return dataCache
    end

    local ok, data = pcall(mw.loadJsonData, 'Module:Musics.json')
    if not ok or type(data) ~= 'table' then
        local title = mw.title.new('Module:Musics.json')
        if not title or not title.exists then
            return nil
        end
        ok, data = pcall(mw.text.jsonDecode, title:getContent() or '')
        if not ok or type(data) ~= 'table' then
            return nil
        end
    end

    dataCache = {}
    for _, music in ipairs(data.musics or data) do
        if type(music) == 'table' and type(music.description) == 'string' then
            if type(music.id) == 'string' and music.id ~= '' then
                dataCache[music.id] = music.description
                dataCache[music.id:lower()] = music.description
            end
            if type(music.name) == 'string' and music.name ~= '' then
                dataCache[music.name] = music.description
                dataCache[music.name:lower()] = music.description
            end
        end
    end
    return dataCache
end

local function formatDescription(description)
    return description:gsub('\\n', '<br>'):gsub('\r\n', '<br>'):gsub('[\r\n]', '<br>')
end

function p.getMusics(frame)
    local data = loadData()
    if not data then
        return ''
    end

    local query = mw.text.trim(tostring(frame.args[1] or ''))
    if query == '' then
        return "''无''"
    end

    local description = data[query] or data[query:lower()]
    return description and formatDescription(description) or "''无''"
end

return p