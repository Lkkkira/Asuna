param([ValidateSet('list', 'speak', 'wave')][string]$Mode = 'list')
$ErrorActionPreference = 'Stop'
[Console]::InputEncoding = New-Object System.Text.UTF8Encoding($false)
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    if ($Mode -eq 'list') {
        $voices = @($speaker.GetInstalledVoices() | Where-Object { $_.Enabled } | ForEach-Object {
            [PSCustomObject]@{ name = $_.VoiceInfo.Name; gender = [string]$_.VoiceInfo.Gender; culture = [string]$_.VoiceInfo.Culture }
        })
        ConvertTo-Json -InputObject $voices -Compress
    } else {
        $settings = [Console]::In.ReadToEnd() | ConvertFrom-Json
        if ($settings.voice) { $speaker.SelectVoice([string]$settings.voice) }
        else { $speaker.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Female) }
        if ($Mode -eq 'wave') { $speaker.SetOutputToWaveFile([string]$settings.path) }
        else { $speaker.SetOutputToDefaultAudioDevice() }
        $speaker.Rate = 0
        $speaker.Speak([string]$settings.text)
    }
} finally { $speaker.Dispose() }
