from app.database.db import Base
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy import String, DateTime, func, Date, ForeignKey, UniqueConstraint, text, BigInteger, Float
from sqlalchemy.dialects.postgresql import JSONB
from typing import Annotated, List, Any, Dict, Optional
from datetime import datetime, UTC, date


intPK = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]
fbref_id_type = Annotated[str, mapped_column(String(100), unique=True)]


class LeagueModel(Base):
    __tablename__ = 'leagues'

    id: Mapped[intPK]
    title: Mapped[str] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    fbref_id: Mapped[str | None] = mapped_column(String(50), unique=False, nullable=True)

    matches: Mapped[List['MatchModel']] = relationship(back_populates='league')


class TeamModel(Base):
    __tablename__ = 'teams'

    id: Mapped[intPK]
    title: Mapped[str] = mapped_column(String(100), index=True)
    fbref_id: Mapped[fbref_id_type]
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )


class PlayerModel(Base):
    __tablename__ = 'players'

    id: Mapped[intPK]
    name: Mapped[str] = mapped_column(String(150))
    fbref_id: Mapped[fbref_id_type]
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)

    stats: Mapped[List['PlayerMatchStatModel']] = relationship(back_populates='player')


class MatchModel(Base):
    __tablename__ = 'matches'

    id: Mapped[intPK]
    fbref_id: Mapped[fbref_id_type]
    date: Mapped[date] = mapped_column(Date, index=True)
    season: Mapped[str] = mapped_column(String(10), index=True)

    league_id: Mapped[int] = mapped_column(ForeignKey('leagues.id'))
    home_team_id: Mapped[int] = mapped_column(ForeignKey('teams.id'))
    away_team_id: Mapped[int] = mapped_column(ForeignKey('teams.id'))

    home_score: Mapped[int | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None] = mapped_column(nullable=True)
    home_xg: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_xg: Mapped[float | None] = mapped_column(Float, nullable=True)

    is_finished: Mapped[bool] = mapped_column(server_default=text('false'))
    details_parsed: Mapped[bool] = mapped_column(server_default=text('false'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        server_default=func.now()
    )

    league: Mapped['LeagueModel'] = relationship(back_populates='matches')
    home_team: Mapped['TeamModel'] = relationship(foreign_keys=[home_team_id])
    away_team: Mapped['TeamModel'] = relationship(foreign_keys=[away_team_id])

    player_stats: Mapped[List['PlayerMatchStatModel']] = relationship(
        back_populates='match',
        cascade='all, delete-orphan'
    )


class PlayerMatchStatModel(Base):
    __tablename__ = 'player_match_stats'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(ForeignKey('matches.id', ondelete='CASCADE'), index=True)
    player_id: Mapped[int] = mapped_column(ForeignKey('players.id', ondelete='CASCADE'), index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey('teams.id', ondelete='CASCADE'))

    minutes: Mapped[int] = mapped_column(server_default=text('0'))
    position: Mapped[str | None] = mapped_column(String(5), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)

    goals: Mapped[int] = mapped_column(server_default=text('0'))
    assists: Mapped[int] = mapped_column(server_default=text('0'))
    shots: Mapped[int] = mapped_column(server_default=text('0'))
    shots_on_target: Mapped[int] = mapped_column(server_default=text('0'))
    xg: Mapped[float] = mapped_column(Float, server_default=text('0.0'))
    npxg: Mapped[float] = mapped_column(Float, server_default=text('0.0'))
    xa: Mapped[float] = mapped_column(Float, server_default=text('0.0'))

    touches: Mapped[int] = mapped_column(server_default=text('0'))
    passes_completed: Mapped[int] = mapped_column(server_default=text('0'))
    passes_attempted: Mapped[int] = mapped_column(server_default=text('0'))
    progressive_carries: Mapped[int] = mapped_column(server_default=text('0'))

    tackles: Mapped[int] = mapped_column(server_default=text('0'))
    interceptions: Mapped[int] = mapped_column(server_default=text('0'))
    blocks: Mapped[int] = mapped_column(server_default=text('0'))

    other_stats: Mapped[Dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))

    match: Mapped['MatchModel'] = relationship(back_populates='player_stats')
    player: Mapped['PlayerModel'] = relationship(back_populates='stats')

    __table_args__ = (
        UniqueConstraint(
            'match_id', 'player_id', name='uix_match_player_stat'
        ),
    )