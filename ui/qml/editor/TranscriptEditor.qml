import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15
import SPVideoStudio.Phase22 1.0
import "../theme"
import "../components"

Item {
    id:root
    property var controller
    property var playbackController
    property string selectedSegmentId:""
    signal exportRequested()
    ColumnLayout { anchors.fill:parent; spacing:Theme.spacing.md
        TranscriptToolbar { Layout.fillWidth:true; controller:root.controller; onExportRequested:root.exportRequested() }
        SplitView { Layout.fillWidth:true; Layout.fillHeight:true; orientation:Qt.Vertical
            ListView { id:transcriptList; SplitView.fillWidth:true; SplitView.fillHeight:true; SplitView.minimumHeight:220; clip:true; spacing:Theme.spacing.sm; model:root.controller?root.controller.segments:null; boundsBehavior:Flickable.StopAtBounds; ScrollBar.vertical:ScrollBar{}
                delegate:TranscriptSegmentRow {
                    required property string segmentId; required property int startMs; required property int endMs; required property string startText; required property string endText; required property string segmentText; required property string originalText; required property bool edited
                    width:transcriptList.width
                    onTextEdited:function(id,value){root.selectedSegmentId=id;if(root.controller){root.controller.editSegment(id,value);WordTiming.load(root.controller.currentProjectId||"",id)}}
                    onResetRequested:function(id){if(root.controller)root.controller.resetSegment(id)}
                    onPlayRequested:function(id,start){root.selectedSegmentId=id;if(root.controller){WordTiming.load(root.controller.currentProjectId||"",id);root.controller.playSegment(root.controller.mediaId,start,true)}}
                }
                footer:Item{width:1;height:Theme.spacing.lg}
            }
            WordTimingEditor { SplitView.fillWidth:true; SplitView.preferredHeight:210; visible:root.selectedSegmentId!==""; fps:30 }
        }
    }
}
